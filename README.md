

## 🚀 Como executar o projeto

### 1. Pré-requisitos

Certifique-se de possuir instalado:

- Python 3.14 ou compatível com as dependências do projeto.
- Git.
- Navegador atualizado.

### 2. Clonar o repositório

```bash
git clone https://github.com/SEU-USUARIO/TransitGraph.git
```

Entre na pasta:

```bash
cd TransitGraph
```

### 3. Criar o ambiente virtual

No Windows:

```powershell
python -m venv venv
```

Ative o ambiente:

```powershell
.\venv\Scripts\Activate.ps1
```

### 4. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 5. Preparar a base de dados

Coloque o arquivo GTFS compactado na pasta:

```text
data/raw/
```

Execute o script de processamento:

```bash
python scripts/build_graph.py --date 2026-11-01
```

O processamento irá construir o grafo a partir das viagens ativas na data informada.

### 6. Iniciar a aplicação

```bash
python run.py
```

Acesse pelo navegador:

```text
http://127.0.0.1:5000
```

## 🧪 Testes

O projeto utiliza Pytest para validar o funcionamento dos algoritmos e das operações do grafo.

Para executar os testes:

```bash
python -m pytest -v
```


**TransitGraph — Explorando a conectividade do transporte público por meio da Teoria dos Grafos.**
