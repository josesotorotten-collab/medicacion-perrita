# Medicación de mi perrita 🐾

App web para registrar medicaciones y recibir recordatorios por WhatsApp.

---

## Correrlo en tu PC (para probar)

### 1. Instalar Python
Si no tenés Python, bajalo de https://python.org (versión 3.11 o mayor). Marcá la opción "Add to PATH".

### 2. Instalar dependencias
Abrí una terminal en la carpeta del proyecto y ejecutá:
```
pip install -r requirements.txt
```

### 3. Iniciar la app
```
python app.py
```
Abrí el navegador en http://localhost:5000

---

## Subir a Railway (gratis, siempre activo)

Railway es una plataforma gratuita para alojar aplicaciones web.

### Paso 1: Crear cuenta
Entrá a https://railway.app y creá una cuenta (podés usar tu cuenta de GitHub).

### Paso 2: Instalar Railway CLI (opcional, podés hacerlo todo desde la web)

### Paso 3: Subir el código
1. Creá un repositorio en GitHub con todos estos archivos.
2. En Railway, hacé clic en "New Project" → "Deploy from GitHub repo".
3. Seleccioná tu repositorio y Railway lo detecta automáticamente.

### Paso 4: Configurar volumen persistente (para que no se pierdan los datos)
En Railway, en tu proyecto, andá a Settings → Volumes → Add Volume.
- Mount path: `/data`
- Luego en Variables, agregá: `DB_PATH = /data/medicaciones.db`

### Paso 5: Listo
Railway te da una URL pública (ej: `mi-perrita.up.railway.app`). ¡Abrila desde el celular!

---

## Configurar WhatsApp (CallMeBot)

1. Guardá el número **+34 644 63 51 09** en tus contactos de WhatsApp como "CallMeBot".
2. Enviá este mensaje exacto desde WhatsApp:
   ```
   I allow callmebot to send me messages
   ```
3. Recibirás tu **API Key** por WhatsApp en pocos segundos.
4. En la app, hacé clic en "⚙️ Configurar WhatsApp" e ingresá:
   - Tu número (con código de país, sin el +). Ejemplo para Argentina: `5491112345678`
   - La API Key que recibiste
5. Hacé clic en "Enviar mensaje de prueba" para verificar que funciona.

---

## Cómo usar la app

- **"✅ Apliqué ahora"**: registra la aplicación en este momento.
- **"🕐 Otra hora"**: te permite ingresar el horario exacto si ya la aplicaste antes.
- **"📋"**: historial de las últimas 30 aplicaciones (podés borrar registros erróneos).

Los recordatorios llegan por WhatsApp exactamente cuando se cumplen las horas de cada medicación.
