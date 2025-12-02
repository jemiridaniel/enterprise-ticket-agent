# Enterprise Ticket Agent (FastAPI + React + ChromaDB + LLM Orchestration)

An end-to-end AI-assisted enterprise helpdesk ticketing system.

The system automatically:
- Generates IT support answers using an LLM
- Suggests engineering actions
- Asks follow-up questions
- Stores contextual embeddings in ChromaDB
- Maintains ongoing threaded conversations
- Provides a clean React UI for real-time interaction

This project showcases a **full LLM agent workflow**, including multi-turn reasoning, vector retrieval, and structured output parsing.


## Features

###  AI Agent Capabilities
- Summaries, action steps, and follow-up questions per ticket  
- Retrieval-augmented reasoning using ChromaDB  
- Full multi-turn conversation thread  
- Detects similar historical incidents  
- Structured JSON outputs for UI rendering  

### Backend (FastAPI)
- `/tickets` → create new ticket  
- `/tickets/{id}/thread` → retrieve full conversation  
- `/tickets/{id}/followup` → send additional user messages  
- Automated prompt orchestration  
- Embedding + similarity search  

### Frontend (React + Vite)
- New ticket creation  
- Ticket history panel  
- Live conversation thread view  
- Follow-up message box  
- Suggested Actions, Questions, and Similar Incidents panel  

### Vector Storage (ChromaDB)
Stores:
- ticket metadata  
- full user & agent message histories  
- embeddings for similarity retrieval  

---

##  Folder Structure

```plaintext
enterprise-ticket-agent/
│
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── routes/
│   │   │   └── tickets.py
│   │   ├── models/
│   │   │   └── tickets.py
│   │   ├── services/
│   │   │   ├── agent_orchestrator.py
│   │   │   └── vector_service.py
│   │   └── utils/
│   ├── chroma/                     # ChromaDB local storage
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.tsx
│   │   ├── api.ts
│   │   └── components/
│   │       └── TicketDetail.tsx
│   ├── public/
│   ├── vite.config.ts
│   ├── index.html
│   └── Dockerfile
│
├── docker-compose.yml
├── LICENSE
└── README.md
