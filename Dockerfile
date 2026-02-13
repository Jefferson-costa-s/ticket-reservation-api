# estagio 1: Builder (o canteiro de obras)
# objetivo: preparar as dependencias e gerar o requirements.txt

FROM python:3.12-slim as builder

# Evita que o python gere arquivos .pyc e bufferize logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# instala o poetry e ferramentas de sistema basica
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

#instala o poetry na versão fixa para eivtar supresas 
RUN pip install poetry==1.7.1

WORKDIR /app

#copia apenas os arquivos de definição de dependencia primeiro
# isso otimiza o cache do Docker: se o project.toml não mudar, ele não reinstala tudo
COPY pyproject.toml poetry.lock ./

# exporta as dependencias do poertry para um requirements.txt padrão
#  por que? o pip é mais leve e mais rapido de instalar no estagio final do que o poetry 
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

#estagio 2: Runtime (casa pronta)

FROM python:3.12-slim as Runtime

#cria um usuario não-root por segurança (besta practice de segurança)
#Se invadirem o container, não terão acesso ao root do sisetma

RUN groupadd -r appuser && useradd -r -g appuser appuser

WORKDIR /app

#copia o requirements.txt GERADO no estagio anterior (builder)
COPY --from=builder /app/requirements.txt .

#Instala as dependencias usando pip (sem precisar do poetry aqui)
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini ./
COPY migrations ./migrations
#copia o codigo da aplicaçao 
COPY app ./app

#ajusta as permissoes para usuario não root
RUN chown -R appuser:appuser /app

#tROCA PARA USUARIO SEGURO
USER appuser

# expoe a porta que o Uvicorn vai usar 
EXPOSE 8000

#comando de iniciaçização 
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
