#!/usr/bin/env python
"""
Script de inicialização da aplicação FastAPI com Uvicorn
"""
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:api",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
