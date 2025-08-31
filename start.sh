#!/bin/bash

# Ativar virtualenv se você usa (opcional)
# source ./venv/bin/activate  

# Instalar dependências
pip install --upgrade pip
pip install -r requirements.txt

# Rodar a aplicação Flask em modo dev
python -m flask run --host=0.0.0.0 --port=3000