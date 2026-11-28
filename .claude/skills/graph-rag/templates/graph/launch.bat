@echo off
rem Open the explorer. No bake needed — the app reads the journals'
rem generated site/*.js bundles directly.
start "" "%~dp0site\index.html"
