#  MediScope

> An assistant that answers questions about medications using only
> official sources, and cites every one of them.

## What MediScope does

You ask a question about a medication, for example *"Can I take ibuprofen
during pregnancy?"* or *"What is the paracetamol dosage for children?"*.
MediScope:

1. **retrieves** relevant passages from patient leaflets and Summaries of
   Product Characteristics (SmPC) in the French public drug database
   (BDPM, ANSM), and from PubMed;
2. **generates** an answer grounded only in those passages;
3. **cites** each source it used, with a link to the original document;
4. **declines** to answer when the question is out of scope or the
   sources are insufficient.

## Tech stack

- **Frontend**: React + Vite
- **API**: NestJS (Domain-Driven Design, hexagonal architecture)
- **AI engine**: FastAPI, LangChain, Postgres/pgvector, fine-tuned LLM (QLoRA)
- **Infrastructure**: Terraform, GCP Cloud Run, GitHub Actions
- **Observability**: Datadog (system health), Langfuse (LLM answer quality)

> ⚠️ **Disclaimer**: MediScope is not a medical device and does not replace
> advice from a doctor or pharmacist.


