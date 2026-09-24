#!/bin/bash
# Copia los registros (transcripts) de Claude Code de ESTE proyecto a ./claude_logs
# Se ejecuta solo desde los hooks de .claude/settings.json de esta carpeta.
INPUT=$(cat)
TRANSCRIPT=$(echo "$INPUT" | jq -r '.transcript_path // empty')
PROJECT_DIR="${CLAUDE_PROJECT_DIR:-$(pwd)}"
[ -z "$TRANSCRIPT" ] && exit 0
SRC_DIR=$(dirname "$TRANSCRIPT")
[ -d "$SRC_DIR" ] || exit 0
mkdir -p "$PROJECT_DIR/claude_logs"
# Sin --delete: los registros se conservan aunque Claude limpie los originales
rsync -a --chmod=Du=rwx,Dgo=rx,Fu=rw,Fgo=r "$SRC_DIR/" "$PROJECT_DIR/claude_logs/" >/dev/null 2>&1
exit 0
