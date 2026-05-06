import os, time, pickle, asyncio
import ollama, faiss, numpy as np
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastembed import TextEmbedding 

# -------------------
# Settings
# -------------------
MODEL_NAME = "qwen2.5:0.5b-instruct-q4_0"
NUM_THREAD = 4
NUM_PREDICT = 32          
TOP_K = 1
CONTEXT_TOP = 1
CHUNK_SIZE = 256
OVERLAP = 16           
DOCS_DIR = "./docs"
EMBED_CACHE = "./embeddings.pkl"
SYSTEM_PROMPT = "Local RAG assistant. Answer strictly from context. Be precise and concise, with no abrupt answers."

# -------------------
# Lifespan
# -------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    print(f"🔥 Warming {MODEL_NAME}...")
    try:
        client.chat(
            model=MODEL_NAME,
            messages=[{"role":"user","content":"."}],
            options={"num_predict":1, "num_thread":NUM_THREAD}
        )
        print("✅ Ready.")
    except Exception as e:
        print(f"⚠️ Warmup skipped: {e}")
    yield

# -------------------
# Initialize
# -------------------
app = FastAPI(title="Ultra-Fast RAG", lifespan=lifespan)
client = ollama.Client()
embedder = TextEmbedding(model_name="BAAI/bge-small-en-v1.5") 

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# -------------------
# Logic Classes
# -------------------
class Retriever:
    def __init__(self, docs_dir=DOCS_DIR):
        if os.path.exists(EMBED_CACHE):
            print("⚡ Loading cached embeddings...")
            with open(EMBED_CACHE, "rb") as f:
                self.chunks, self.embs = pickle.load(f)
        else:
            print("⚡ Computing embeddings...")
            self.chunks = self.load_docs(docs_dir)
            self.embs = np.array(list(embedder.embed(self.chunks)), dtype=np.float32)
            with open(EMBED_CACHE, "wb") as f:
                pickle.dump((self.chunks, self.embs), f)

        dim = self.embs.shape[1]
        self.index = faiss.IndexFlatIP(dim)
        faiss.normalize_L2(self.embs)
        self.index.add(self.embs)

    def load_docs(self, docs_dir):
        texts = []
        if os.path.isdir(docs_dir):
            for f in os.listdir(docs_dir):
                if f.endswith(".txt"):
                    with open(os.path.join(docs_dir,f), encoding="utf-8") as fp:
                        texts.append(fp.read())
        
        chunks = []
        for doc in texts:
            words = doc.split()
            step = CHUNK_SIZE - OVERLAP
            for i in range(0, len(words), step):
                chunks.append(" ".join(words[i:i+CHUNK_SIZE]))
        return chunks

    def retrieve(self, query):
        if len(query.split()) <= 2:
            return ["No context needed."]
        q = np.array(list(embedder.embed([query])), dtype=np.float32)
        faiss.normalize_L2(q)
        _, idx = self.index.search(q, TOP_K)
        return [self.chunks[i] for i in idx[0][:CONTEXT_TOP]]

retriever = Retriever()

# -------------------
# Routes
# -------------------
@app.get("/", response_class=HTMLResponse)
def root():
    try:
        with open("client/index.html", "r", encoding="utf-8") as f:
            return f.read()
    except:
        return "index.html missing"

@app.post("/api/chat")
async def chat_api(req: dict):
    start = time.time()
    msg = req.get("message", "")
    ctx = "\n".join(retriever.retrieve(msg))
    
    # Stateless chat: no history
    loop = asyncio.get_running_loop()
    response = await loop.run_in_executor(None, lambda: client.chat(
        model=MODEL_NAME,
        messages=[
            {"role":"system", "content":SYSTEM_PROMPT},
            {"role":"user", "content": f"C: {ctx}\nQ: {msg}"}
        ],
        options={"num_predict":NUM_PREDICT, "temperature":0.1, "num_thread":NUM_THREAD}
    ))

    answer = response['message']['content'].strip()
    return {"answer": f"{answer}\n\n⏱️ {time.time()-start:.3f}s"}

# -------------------
# Static Mounting
# -------------------
if os.path.exists("client"):
    app.mount("/css", StaticFiles(directory="client/css"), name="css")
    app.mount("/js", StaticFiles(directory="client/js"), name="js")

# -------------------
# Execution
# -------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
