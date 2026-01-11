import random
import threading
import time
from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

TAMANHO = 10
DIRECOES = [(1,0), (-1,0), (0,1), (0,-1)]

# ----------------------------
# AGENTES
# ----------------------------

class AgenteBase:
    def __init__(self, id, x, y, tipo):
        self.id = id
        self.x = x
        self.y = y
        self.vivo = True
        self.escudo = False
        self.tipo = tipo
        self.passos = 0
        self.tesouros = 0

    def decidir(self, ambiente):
        return random.choice(DIRECOES)

class AgenteDecisionTree(AgenteBase):
    def decidir(self, ambiente):
        random.shuffle(DIRECOES)
        for dx, dy in DIRECOES:
            nx, ny = self.x + dx, self.y + dy
            if 0 <= nx < TAMANHO and 0 <= ny < TAMANHO:
                if ambiente.grid[nx][ny] != "B":
                    return dx, dy
        return random.choice(DIRECOES)

class AgenteKNN(AgenteBase):
    def decidir(self, ambiente):
        livres = []
        for dx, dy in DIRECOES:
            nx, ny = self.x + dx, self.y + dy
            if 0 <= nx < TAMANHO and 0 <= ny < TAMANHO:
                if ambiente.grid[nx][ny] == "L":
                    livres.append((dx, dy))
        return random.choice(livres) if livres else random.choice(DIRECOES)

class AgenteNaiveBayes(AgenteBase):
    def decidir(self, ambiente):
        return random.choice(DIRECOES)

# ----------------------------
# AMBIENTE
# ----------------------------

class Ambiente:
    def __init__(self, bombas_pct=0.5):
        self.bombas_pct = bombas_pct
        self.grid = self.gerar_grid()
        self.agentes = []
        self.logs = []
        self.ativo = False
        self.tempo_max = 0
        self.inicio = None

    def gerar_grid(self):
        grid = []
        for _ in range(TAMANHO):
            linha = []
            for _ in range(TAMANHO):
                linha.append("B" if random.random() < self.bombas_pct else "L")
            grid.append(linha)

        for _ in range(5):
            x = random.randint(0, TAMANHO - 1)
            y = random.randint(0, TAMANHO - 1)
            grid[x][y] = "T"

        return grid

    def adicionar_agentes(self, n_por_modelo):
        self.agentes = []
        classes = [AgenteDecisionTree, AgenteKNN, AgenteNaiveBayes]
        id_global = 0

        for cls in classes:
            for _ in range(n_por_modelo):
                while True:
                    x = random.randint(0, TAMANHO - 1)
                    y = random.randint(0, TAMANHO - 1)
                    if self.grid[x][y] == "L":
                        self.agentes.append(cls(id_global, x, y, cls.__name__))
                        id_global += 1
                        break

ambiente = Ambiente()

# ----------------------------
# SIMULAÇÃO
# ----------------------------

def passo_simulacao():
    for agente in ambiente.agentes:
        if not agente.vivo:
            continue

        dx, dy = agente.decidir(ambiente)
        nx, ny = agente.x + dx, agente.y + dy

        if 0 <= nx < TAMANHO and 0 <= ny < TAMANHO:
            agente.x, agente.y = nx, ny
            agente.passos += 1
            celula = ambiente.grid[nx][ny]

            if celula == "B":
                if agente.escudo:
                    agente.escudo = False
                    ambiente.logs.append(f"{agente.tipo} desativou bomba.")
                else:
                    agente.vivo = False
                    ambiente.logs.append(f"{agente.tipo} morreu.")
            elif celula == "T":
                agente.escudo = True
                agente.tesouros += 1
                ambiente.logs.append(f"{agente.tipo} encontrou tesouro.")

def loop():
    while True:
        if ambiente.ativo:
            if time.time() - ambiente.inicio >= ambiente.tempo_max:
                ambiente.ativo = False
                ambiente.logs.append("⏱ Exploração terminada.")
            else:
                passo_simulacao()
        time.sleep(0.6)

threading.Thread(target=loop, daemon=True).start()

# ----------------------------
# API
# ----------------------------

@app.get("/estado")
def estado():
    grid_vis = [[ambiente.grid[i][j] for j in range(TAMANHO)] for i in range(TAMANHO)]

    for a in ambiente.agentes:
        if a.vivo:
            if "Decision" in a.tipo:
                grid_vis[a.x][a.y] = "D"
            elif "KNN" in a.tipo:
                grid_vis[a.x][a.y] = "K"
            else:
                grid_vis[a.x][a.y] = "N"

    return {
        "grid": grid_vis,
        "logs": ambiente.logs[-60:]
    }

@app.post("/configurar")
def configurar(cfg: dict = Body(...)):
    global ambiente
    bombas = cfg["bombas"]
    agentes = cfg["agentes"]
    tempo = cfg["tempo"]

    ambiente = Ambiente(bombas)
    ambiente.adicionar_agentes(agentes)
    ambiente.tempo_max = tempo
    ambiente.inicio = time.time()
    ambiente.ativo = True
    ambiente.logs.append(
        f"Exploração iniciada | Bombas: {int(bombas*100)}% | "
        f"{agentes} agentes por modelo | Tempo: {tempo}s"
    )
    return {"ok": True}

@app.post("/avaliar/{abordagem}")
def avaliar(abordagem: str):
    ambiente.logs.append(f"📊 Avaliação pela Abordagem {abordagem}")
    return {"ok": True}
