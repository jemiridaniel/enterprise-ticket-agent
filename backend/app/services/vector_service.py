from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import chromadb
from chromadb.utils import embedding_functions

from ..config import settings


def _now_iso() -> str:
    """UTC timestamp in ISO 8601 with Z."""
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


class VectorStore:
    """
    Thin wrapper around a ChromaDB collection for tickets + messages.

    We store:
      - kind: "ticket" or "message"
      - ticket_id: logical ticket id (e.g. TCK-XXXX)
      - subject, severity, status, created_at (for ticket roots)
      - role, created_at (for messages)
      - document text: description / message content
    """

    def __init__(self) -> None:
        client = chromadb.PersistentClient(path=settings.VECTOR_DB_DIR)

        # Use a lightweight sentence-transformer embedding
        embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="all-MiniLM-L6-v2"
        )

        self.collection = client.get_or_create_collection(
            name="tickets",
            embedding_function=embed_fn,
        )

    # ---------- Ticket root docs ----------

    def add_ticket_root(
        self,
        ticket_id: str,
        subject: str,
        description: str,
        user_upn: str,
        severity: str,
        status: str = "open",
        created_at: Optional[str] = None,
    ) -> None:
        """
        Store the main ticket record as a single vector doc.
        The id of this doc = ticket_id.
        """
        if created_at is None:
            created_at = _now_iso()

        metadata: Dict[str, Any] = {
            "kind": "ticket",
            "ticket_id": ticket_id,
            "subject": subject,
            "user_upn": user_upn,
            "severity": severity,
            "status": status,
            "created_at": created_at,
        }

        self.collection.add(
            ids=[ticket_id],
            documents=[description],
            metadatas=[metadata],
        )

    # ---------- Messages ----------

    def append_message(
        self,
        ticket_id: str,
        role: str,
        content: str,
        created_at: Optional[str] = None,
    ) -> str:
        """
        Append a message in the conversation thread for a ticket.
        Stored as a separate doc with kind="message".
        """
        if created_at is None:
            created_at = _now_iso()

        msg_id = f"{ticket_id}-msg-{uuid4().hex[:8]}"

        metadata: Dict[str, Any] = {
            "kind": "message",
            "ticket_id": ticket_id,
            "role": role,
            "created_at": created_at,
        }

        self.collection.add(
            ids=[msg_id],
            documents=[content],
            metadatas=[metadata],
        )

        return msg_id

    # ---------- Similar incidents ----------

    def query_similar(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        """
        Find similar ticket roots (kind="ticket") for a given text.
        Returns a list of dicts with ticket_id, subject, description, similarity_score.
        """
        res = self.collection.query(
            query_texts=[query],
            n_results=k,
            where={"kind": "ticket"},  # <-- single operator
            include=["documents", "metadatas", "distances"],
        )

        docs_list = res.get("documents", [[]])[0] if res.get("documents") else []
        metas_list = res.get("metadatas", [[]])[0] if res.get("metadatas") else []
        dists_list = res.get("distances", [[]])[0] if res.get("distances") else []

        similar: List[Dict[str, Any]] = []
        for meta, doc, dist in zip(metas_list, docs_list, dists_list):
            similar.append(
                {
                    "ticket_id": meta.get("ticket_id"),
                    "subject": meta.get("subject", ""),
                    "description": doc,
                    # Convert distance to a "similarity" feel (1 - dist)
                    "similarity_score": float(1.0 - dist) if dist is not None else None,
                }
            )

        return similar

    # ---------- History list ----------

    def list_tickets(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Return lightweight ticket items for the history sidebar.
        """
        res = self.collection.get(
            where={"kind": "ticket"},  # valid where – one operator
            include=["metadatas"],
        )

        metadatas = res.get("metadatas", []) or []

        items: List[Dict[str, Any]] = []
        for meta in metadatas:
            items.append(
                {
                    "ticket_id": meta.get("ticket_id"),
                    "subject": meta.get("subject", ""),
                    "severity": meta.get("severity", "medium"),
                    "status": meta.get("status", "open"),
                    "created_at": meta.get("created_at", _now_iso()),
                }
            )

        # Sort newest first
        items.sort(key=lambda x: x.get("created_at") or "", reverse=True)
        return items[:limit]

    # ---------- Ticket + messages ----------

    def get_ticket_and_messages(self, ticket_id: str) -> Dict[str, Any]:
        """
        Pull the ticket root + all messages for a ticket_id in one shot.
        Fixes: we only use where={"ticket_id": ticket_id} to avoid
        the 'Expected where to have exactly one operator' chroma error.
        """
        res = self.collection.get(
            where={"ticket_id": ticket_id},  # <-- single key, no chroma error
            include=["documents", "metadatas"],
        )

        metadatas = res.get("metadatas", []) or []
        documents = res.get("documents", []) or []

        ticket_meta: Optional[Dict[str, Any]] = None
        messages: List[Dict[str, Any]] = []

        for meta, doc in zip(metadatas, documents):
            kind = meta.get("kind")

            if kind == "ticket" and ticket_meta is None:
                # root ticket
                ticket_meta = dict(meta)
                ticket_meta["description"] = doc
            elif kind == "message":
                messages.append(
                    {
                        "role": meta.get("role", "user"),
                        "content": doc,
                        "created_at": meta.get("created_at", _now_iso()),
                    }
                )

        # sort messages by created_at
        messages.sort(key=lambda m: m.get("created_at") or "")

        return {
            "ticket": ticket_meta,
            "messages": messages,
        }

    # ---------- Close ticket ----------

    def close_ticket(self, ticket_id: str) -> None:
        """
        Mark a ticket as closed in its root metadata.
        """
        res = self.collection.get(
            where={"ticket_id": ticket_id},  # again: single operator
            include=["metadatas"],
        )

        ids = res.get("ids", []) or []
        metadatas = res.get("metadatas", []) or []

        for _id, meta in zip(ids, metadatas):
            if meta.get("kind") == "ticket":
                meta = dict(meta)
                meta["status"] = "closed"
                self.collection.update(
                    ids=[_id],
                    metadatas=[meta],
                )
                return

        raise ValueError(f"Ticket {ticket_id} not found")


# Singleton used across the app
vector_store = VectorStore()
