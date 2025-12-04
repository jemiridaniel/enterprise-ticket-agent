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
    """

    def __init__(self) -> None:
        print(">>> INITIALIZING VECTORSTORE")

        client = chromadb.PersistentClient(path=settings.VECTOR_DB_DIR)
        print(">>> CLIENT CREATED")

        print(">>> LOADING EMBEDDING FN")
        embed_fn = embedding_functions.DefaultEmbeddingFunction()
        print(">>> EMBEDDING FN LOADED")

        print(">>> CREATING COLLECTION")
        self.collection = client.get_or_create_collection(
            name="tickets",
            embedding_function=embed_fn,
        )
        print(">>> COLLECTION READY")

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

        if created_at is None:
            created_at = _now_iso()

        metadata = {
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

        if created_at is None:
            created_at = _now_iso()

        msg_id = f"{ticket_id}-msg-{uuid4().hex[:8]}"

        metadata = {
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

        res = self.collection.query(
            query_texts=[query],
            n_results=k,
            where={"kind": "ticket"},
            include=["documents", "metadatas", "distances"],
        )

        docs = res.get("documents", [[]])[0]
        metas = res.get("metadatas", [[]])[0]
        dists = res.get("distances", [[]])[0]

        similar = []
        for meta, doc, dist in zip(metas, docs, dists):
            similar.append(
                {
                    "ticket_id": meta.get("ticket_id"),
                    "subject": meta.get("subject", ""),
                    "description": doc,
                    "similarity_score": float(1 - dist) if dist is not None else None,
                }
            )

        return similar

    # ---------- History ----------

    def list_tickets(self, limit: int = 50) -> List[Dict[str, Any]]:

        res = self.collection.get(
            where={"kind": "ticket"},
            include=["metadatas"],
        )

        items = []
        for meta in res.get("metadatas", []):
            items.append(
                {
                    "ticket_id": meta.get("ticket_id"),
                    "subject": meta.get("subject", ""),
                    "severity": meta.get("severity", "medium"),
                    "status": meta.get("status", "open"),
                    "created_at": meta.get("created_at", _now_iso()),
                }
            )

        items.sort(key=lambda x: x["created_at"], reverse=True)
        return items[:limit]

    # ---------- Ticket + Messages ----------

    def get_ticket_and_messages(self, ticket_id: str) -> Dict[str, Any]:

        res = self.collection.get(
            where={"ticket_id": ticket_id},
            include=["documents", "metadatas"],
        )

        metadatas = res.get("metadatas", [])
        documents = res.get("documents", [])

        ticket_meta = None
        messages = []

        for meta, doc in zip(metadatas, documents):
            if meta.get("kind") == "ticket":
                ticket_meta = dict(meta)
                ticket_meta["description"] = doc
            else:
                messages.append(
                    {
                        "role": meta.get("role"),
                        "content": doc,
                        "created_at": meta.get("created_at"),
                    }
                )

        messages.sort(key=lambda m: m["created_at"])

        return {"ticket": ticket_meta, "messages": messages}

    # ---------- Close ticket ----------

    def close_ticket(self, ticket_id: str):

        res = self.collection.get(
            where={"ticket_id": ticket_id},
            include=["metadatas"],
        )

        ids = res.get("ids", [])
        metas = res.get("metadatas", [])

        for _id, meta in zip(ids, metas):
            if meta.get("kind") == "ticket":
                new_meta = dict(meta)
                new_meta["status"] = "closed"

                self.collection.update(
                    ids=[_id],
                    metadatas=[new_meta],
                )
                return

        raise ValueError(f"Ticket {ticket_id} not found")


# Singleton instance
vector_store = VectorStore()
