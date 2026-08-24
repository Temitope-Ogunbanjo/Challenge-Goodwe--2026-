from pathlib import Path
from fastapi import FastAPI, Request
from Fastapi.templating import Jinja2Templates

App = FastAPI()

def SetarTemplates():
    pathTemplates = Path(__file__).resolve().parent.parent / "frontend" / "paginas"
    return Jinja2Templates(directory=pathTemplates)

Templates = SetarTemplates()

@App.get("/{nome_pagina}")
def Carregar(request : Request, Nome: str):
    Arquivo = f"{Nome}.html"
    return Templates.TemplatesResponse(Arquivo, {"request" : Request})

#Carregar é para a lógica de footer/header padronizados