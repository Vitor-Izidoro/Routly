#!/usr/bin/env bash
cd -- "$(dirname -- "${BASH_SOURCE[0]}")" || exit 1
export MPLBACKEND=QtAgg
while true; do
    .venv/bin/python estrela.py
    read -r -p 'Executar outra consulta? [S/n]: ' resposta
    case "$resposta" in n|N) break ;; esac
done
