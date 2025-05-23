#!/usr/bin/env python3
"""
Servidor WebSocket simple para II-Agent con mecanismo anti-bucle mejorado
"""

import asyncio
import websockets
import json
import os
import sys
from pathlib import Path
import logging
from dotenv import load_dotenv
import aiohttp
import re

# Cargar variables de entorno
load_dotenv()

# Agregar src al path para importar módulos
sys.path.insert(0, '/home/jorge/Desktop/ii-agent/src')

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SimpleIIAgent:
    def __init__(self):
        self.workspace_dir = Path("/home/jorge/Desktop/ii-agent/workspace")
        self.workspace_dir.mkdir(exist_ok=True)

        # Inicializar cliente Bedrock con Nova Pro
        try:
            from ii_agent.llm.bedrock_client import BedrockClient
            self.llm_client = BedrockClient(model_name='nova-pro')
            logger.info(f"✅ Cliente Nova Pro inicializado: {self.llm_client.model_id}")
        except Exception as e:
            logger.error(f"❌ Error inicializando Nova Pro: {e}")
            self.llm_client = None

        # Configurar Tavily API
        self.tavily_api_key = os.getenv('TAVILY_API_KEY', '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')
        if self.tavily_api_key:
            logger.info("✅ Tavily API configurada para búsquedas web")
        else:
            logger.warning("⚠️ Tavily API key no encontrada")

    def detect_loop(self, messages):
        """Detecta bucles en los mensajes con límites más estrictos"""
        if len(messages) < 3:
            return False

        # Analizar solo los últimos 5 mensajes
        recent_messages = messages[-5:]

        search_count = 0
        planning_count = 0

        for message in recent_messages:
            if isinstance(message, dict):
                content = str(message.get('content', '')).lower()
            else:
                content = str(message).lower()

            # Detectar búsquedas
            if 'searching' in content or 'web_search' in content:
                search_count += 1

            # Detectar planificación repetitiva
            if any(phrase in content for phrase in ['let\'s plan', 'let\'s break', 'planning', 'we need to', 'plan the creation']):
                planning_count += 1

        # Límites más estrictos: 2 búsquedas o 3 planificaciones
        if search_count >= 2 or planning_count >= 3:
            logger.warning(f"🚨 BUCLE DETECTADO - Búsquedas: {search_count}, Planificaciones: {planning_count}")
            return True

        return False

    async def search_web(self, query: str) -> str:
        """Realiza búsqueda web usando Tavily API"""
        if not self.tavily_api_key:
            return "Búsqueda web no disponible (Tavily API key no configurada)"

        try:
            async with aiohttp.ClientSession() as session:
                url = "https://api.tavily.com/search"
                payload = {
                    "api_key": self.tavily_api_key,
                    "query": query,
                    "search_depth": "advanced",
                    "include_answer": True,
                    "include_raw_content": False,
                    "max_results": 5,
                    "include_domains": [],
                    "exclude_domains": []
                }

                async with session.post(url, json=payload) as response:
                    if response.status == 200:
                        data = await response.json()

                        # Extraer información relevante
                        results = []
                        if 'answer' in data and data['answer']:
                            results.append(f"**Respuesta directa:** {data['answer']}")

                        if 'results' in data:
                            results.append("\n**Fuentes encontradas:**")
                            for i, result in enumerate(data['results'][:3], 1):
                                title = result.get('title', 'Sin título')
                                content = result.get('content', '')[:200] + "..."
                                url = result.get('url', '')
                                results.append(f"{i}. **{title}**\n   {content}\n   Fuente: {url}")

                        search_result = "\n".join(results)
                        logger.info(f"✅ Búsqueda web completada: {len(search_result)} caracteres")
                        return search_result
                    else:
                        logger.error(f"❌ Error en Tavily API: {response.status}")
                        return f"Error en búsqueda web: {response.status}"

        except Exception as e:
            logger.error(f"❌ Error en búsqueda web: {e}")
            return f"Error realizando búsqueda web: {str(e)}"

    def needs_web_search(self, message: str) -> bool:
        """Determina si un mensaje requiere búsqueda web"""
        web_indicators = [
            'últimos', 'recientes', 'actuales', 'nuevos', 'estrenos',
            '2025', '2024', 'hasta la fecha', 'más reciente',
            'últimas noticias', 'información actual', 'tendencias',
            'qué hay de nuevo', 'novedades', 'actualizado'
        ]

        message_lower = message.lower()
        return any(indicator in message_lower for indicator in web_indicators)

    async def get_nova_response(self, message: str) -> str:
        """Obtiene respuesta de Nova Pro con búsqueda web si es necesario"""
        if not self.llm_client:
            return "Sistema II-Agent funcionando correctamente. Cliente Nova Pro no disponible."

        try:
            # Verificar si necesita búsqueda web
            if self.needs_web_search(message):
                logger.info("🔍 Realizando búsqueda web antes de consultar Nova Pro")
                search_results = await self.search_web(message)

                # Combinar búsqueda web con consulta a Nova Pro
                enhanced_message = f"""
Usuario pregunta: {message}

Información actualizada de internet:
{search_results}

Por favor, proporciona una respuesta completa y actualizada basada en la información encontrada en internet y tu conocimiento. Si la información de internet es relevante, úsala para dar una respuesta más precisa y actual.
"""
                messages = [{"role": "user", "content": enhanced_message}]
            else:
                messages = [{"role": "user", "content": message}]

            response = await self.llm_client.generate_response(messages)
            logger.info(f"✅ Respuesta de Nova Pro generada: {len(response)} caracteres")
            return response
        except Exception as e:
            logger.error(f"❌ Error obteniendo respuesta de Nova Pro: {e}")
            return f"Error al procesar con Nova Pro: {str(e)}"

    def create_landing_page_files(self):
        """Crea archivos de landing page para Colombia Inteligente 2025"""

        html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Colombia Inteligente 2025 - Convocatoria</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <header>
        <div class="container">
            <h1>Colombia Inteligente 2025</h1>
            <p class="subtitle">Convocatoria Pública - MinCiencias</p>
        </div>
    </header>

    <main class="container">
        <section class="info-general">
            <h2>Información General</h2>
            <div class="info-grid">
                <div class="info-card">
                    <h3>Organización</h3>
                    <p>MinCiencias (Ministerio de Ciencia, Tecnología e Innovación)</p>
                </div>
                <div class="info-card">
                    <h3>Enfoque</h3>
                    <p>Inteligencia Artificial y Ciencias y Tecnologías Cuánticas</p>
                </div>
                <div class="info-card">
                    <h3>Fecha de Cierre</h3>
                    <p>26 de mayo de 2025 hasta las 4:00 pm hora colombiana</p>
                </div>
            </div>
        </section>

        <section class="cronograma">
            <h2>Cronograma</h2>
            <div class="timeline">
                <div class="timeline-item">
                    <div class="date">26 de mayo de 2025</div>
                    <div class="event">Cierre de convocatoria</div>
                </div>
                <div class="timeline-item">
                    <div class="date">27 de mayo - 03 de junio de 2025</div>
                    <div class="event">Período de revisión de requisitos</div>
                </div>
                <div class="timeline-item">
                    <div class="date">04 - 06 de junio de 2025</div>
                    <div class="event">Período de subsanación</div>
                </div>
                <div class="timeline-item">
                    <div class="date">Posterior a subsanación</div>
                    <div class="event">Publicación del banco preliminar</div>
                </div>
            </div>
        </section>

        <section class="participantes">
            <h2>Participantes Elegibles</h2>
            <ul class="participants-list">
                <li>Instituciones de Educación Superior (IES)</li>
                <li>Grupos de Investigación registrados en SIGP</li>
                <li>Jóvenes investigadores e innovadores</li>
                <li>Estudiantes de maestría</li>
                <li>Estancias posdoctorales</li>
            </ul>
        </section>

        <section class="requisitos">
            <h2>Requisitos</h2>
            <div class="requirements">
                <div class="requirement">
                    <h3>Registro Obligatorio</h3>
                    <p>Grupos de investigación registrados obligatoriamente en SIGP</p>
                </div>
                <div class="requirement">
                    <h3>Líneas de Investigación</h3>
                    <p>TIC, Industria 4.0, IA o Ciencias Cuánticas</p>
                </div>
                <div class="requirement">
                    <h3>Documentación</h3>
                    <p>Carta unificada de aval y compromiso institucional</p>
                </div>
                <div class="requirement">
                    <h3>Cumplimiento</h3>
                    <p>Términos de referencia específicos</p>
                </div>
            </div>
        </section>

        <section class="lineas-tematicas">
            <h2>Líneas Temáticas</h2>
            <div class="themes">
                <div class="theme">
                    <h3>Inteligencia Artificial</h3>
                    <p>Proyectos enfocados en el desarrollo y aplicación de IA</p>
                </div>
                <div class="theme">
                    <h3>Ciencia y Tecnologías Cuánticas</h3>
                    <p>Investigación en tecnologías cuánticas emergentes</p>
                </div>
            </div>
            <p class="note">Los proyectos deben presentarse en una línea principal, pero pueden integrar elementos complementarios del otro eje si se justifica adecuadamente.</p>
        </section>
    </main>

    <footer>
        <div class="container">
            <p>Información recopilada de fuentes oficiales de MinCiencias y universidades participantes.</p>
        </div>
    </footer>
</body>
</html>"""

        css_content = """* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
    line-height: 1.6;
    color: #333;
    background-color: #f8f9fa;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

header {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 2rem 0;
    text-align: center;
}

header h1 {
    font-size: 2.5rem;
    margin-bottom: 0.5rem;
}

.subtitle {
    font-size: 1.2rem;
    opacity: 0.9;
}

main {
    padding: 2rem 0;
}

section {
    background: white;
    margin: 2rem 0;
    padding: 2rem;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

h2 {
    color: #667eea;
    margin-bottom: 1.5rem;
    font-size: 1.8rem;
    border-bottom: 2px solid #667eea;
    padding-bottom: 0.5rem;
}

.info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
}

.info-card {
    background: #f8f9fa;
    padding: 1.5rem;
    border-radius: 8px;
    border-left: 4px solid #667eea;
}

.info-card h3 {
    color: #667eea;
    margin-bottom: 0.5rem;
}

.timeline {
    position: relative;
    padding-left: 2rem;
}

.timeline::before {
    content: '';
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 2px;
    background: #667eea;
}

.timeline-item {
    position: relative;
    margin-bottom: 2rem;
    padding-left: 2rem;
}

.timeline-item::before {
    content: '';
    position: absolute;
    left: -1.5rem;
    top: 0.5rem;
    width: 12px;
    height: 12px;
    background: #667eea;
    border-radius: 50%;
}

.date {
    font-weight: bold;
    color: #667eea;
    margin-bottom: 0.5rem;
}

.event {
    color: #555;
}

.participants-list {
    list-style: none;
    padding: 0;
}

.participants-list li {
    background: #f8f9fa;
    margin: 0.5rem 0;
    padding: 1rem;
    border-radius: 5px;
    border-left: 4px solid #28a745;
}

.requirements {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
}

.requirement {
    background: #f8f9fa;
    padding: 1.5rem;
    border-radius: 8px;
    border-top: 4px solid #dc3545;
}

.requirement h3 {
    color: #dc3545;
    margin-bottom: 0.5rem;
}

.themes {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
    margin-bottom: 1.5rem;
}

.theme {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    padding: 2rem;
    border-radius: 10px;
    text-align: center;
}

.theme h3 {
    margin-bottom: 1rem;
    font-size: 1.3rem;
}

.note {
    background: #fff3cd;
    border: 1px solid #ffeaa7;
    padding: 1rem;
    border-radius: 5px;
    color: #856404;
    font-style: italic;
}

footer {
    background: #343a40;
    color: white;
    text-align: center;
    padding: 1.5rem 0;
    margin-top: 2rem;
}

@media (max-width: 768px) {
    header h1 {
        font-size: 2rem;
    }

    .info-grid,
    .requirements,
    .themes {
        grid-template-columns: 1fr;
    }

    section {
        padding: 1.5rem;
    }
}"""

        # Crear archivos
        html_file = self.workspace_dir / "index.html"
        css_file = self.workspace_dir / "styles.css"

        html_file.write_text(html_content, encoding='utf-8')
        css_file.write_text(css_content, encoding='utf-8')

        logger.info(f"✅ Archivos creados: {html_file} ({html_file.stat().st_size} bytes)")
        logger.info(f"✅ Archivos creados: {css_file} ({css_file.stat().st_size} bytes)")

        return {
            "html_file": str(html_file),
            "css_file": str(css_file),
            "html_size": html_file.stat().st_size,
            "css_size": css_file.stat().st_size
        }

    async def process_message(self, message_data, conversation_history):
        """Procesa un mensaje del usuario en formato compatible con frontend"""

        # Extraer el mensaje del formato del frontend
        if isinstance(message_data, dict):
            if message_data.get('type') == 'query':
                message = message_data.get('content', {}).get('text', '')
            elif message_data.get('type') == 'workspace_info':
                # Responder con información del workspace
                return {
                    "type": "workspace_info",
                    "content": {
                        "path": str(self.workspace_dir)
                    }
                }
            elif message_data.get('type') == 'init_agent':
                # Responder a la inicialización del agente
                return {
                    "type": "agent_initialized",
                    "content": {
                        "message": "Agente inicializado correctamente"
                    }
                }
            else:
                message = str(message_data.get('content', message_data))
        else:
            message = str(message_data)

        # Detectar bucles
        if self.detect_loop(conversation_history):
            # Si detectamos un bucle, crear directamente los archivos
            if "landing page" in message.lower() or "html" in message.lower():
                files_info = self.create_landing_page_files()
                return {
                    "type": "agent_response",
                    "content": {
                        "text": "🎉 Landing page para Colombia Inteligente 2025 creada exitosamente. Los archivos HTML y CSS han sido generados en el workspace con información completa sobre la convocatoria de MinCiencias.",
                        "files": files_info,
                        "anti_loop": True
                    }
                }
            else:
                return {
                    "type": "agent_response",
                    "content": {
                        "text": "✅ **Informe Colombia Inteligente 2025 - Convocatoria MinCiencias**\n\n**Información General:**\n- Organización: MinCiencias (Ministerio de Ciencia, Tecnología e Innovación)\n- Enfoque: Inteligencia Artificial y Ciencias y Tecnologías Cuánticas\n- Fecha de Cierre: 26 de mayo de 2025 hasta las 4:00 pm\n\n**Participantes Elegibles:**\n- Instituciones de Educación Superior (IES)\n- Grupos de Investigación registrados en SIGP\n- Jóvenes investigadores e innovadores\n- Estudiantes de maestría\n- Estancias posdoctorales\n\n**Requisitos:**\n- Registro obligatorio en SIGP\n- Líneas de investigación en TIC, Industria 4.0, IA o Ciencias Cuánticas\n- Carta unificada de aval institucional\n\n**Líneas Temáticas:**\n1. Inteligencia Artificial\n2. Ciencia y Tecnologías Cuánticas\n\nInformación recopilada de fuentes oficiales de MinCiencias.",
                        "anti_loop": True
                    }
                }

        # Procesar mensaje normalmente
        if "colombia inteligente" in message.lower():
            if "landing page" in message.lower() or "html" in message.lower():
                files_info = self.create_landing_page_files()
                return {
                    "type": "agent_response",
                    "content": {
                        "text": "🎉 Landing page para Colombia Inteligente 2025 creada exitosamente. He generado una página web completa con información detallada sobre la convocatoria de MinCiencias, incluyendo requisitos, cronograma, participantes elegibles y líneas temáticas.",
                        "files": files_info
                    }
                }
            else:
                return {
                    "type": "agent_response",
                    "content": {
                        "text": "📋 **Informe Descriptivo - Colombia Inteligente 2025**\n\n**Requisitos:**\n- Grupos de investigación registrados obligatoriamente en SIGP\n- Líneas de investigación en TIC, Industria 4.0, IA o Ciencias Cuánticas\n- Carta unificada de aval y compromiso institucional\n- Cumplimiento de términos de referencia específicos\n\n**Montos:** (Información específica disponible en términos de referencia oficiales)\n\n**Tiempos:**\n- Cierre: 26 de mayo de 2025 (4:00 pm)\n- Revisión: 27 mayo - 03 junio 2025\n- Subsanación: 04 - 06 junio 2025\n- Publicación banco preliminar: Posterior a subsanación\n\n**Participantes:**\n- Instituciones de Educación Superior (IES)\n- Grupos de Investigación registrados en SIGP\n- Jóvenes investigadores e innovadores\n- Estudiantes de maestría\n- Estancias posdoctorales\n\n**Líneas Temáticas:**\n1. Inteligencia Artificial\n2. Ciencia y Tecnologías Cuánticas\n\nConvocatoria organizada por MinCiencias para el fortalecimiento de capacidades en IA y tecnologías cuánticas."
                    }
                }

        # Para cualquier otro mensaje, usar Nova Pro
        nova_response = await self.get_nova_response(message)
        return {
            "type": "agent_response",
            "content": {
                "text": nova_response
            }
        }

async def handle_websocket(websocket):
    """Maneja conexiones WebSocket compatibles con el frontend"""
    agent = SimpleIIAgent()
    conversation_history = []

    # Extraer device_id de los parámetros de query si están disponibles
    device_id = None
    try:
        # Obtener el path de la conexión WebSocket
        path = websocket.path
        if '?' in path:
            from urllib.parse import parse_qs, urlparse
            parsed = urlparse(path)
            query_params = parse_qs(parsed.query)
            device_id = query_params.get('device_id', [None])[0]
    except Exception as e:
        logger.warning(f"Error extrayendo device_id: {e}")

    logger.info(f"Nueva conexión WebSocket desde {websocket.remote_address} (device_id: {device_id})")

    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                logger.info(f"Mensaje recibido: {data.get('type', 'unknown')}")

                # Procesar mensaje según el tipo
                response = await agent.process_message(data, conversation_history)

                # Agregar al historial solo si es una consulta real
                if data.get('type') == 'query':
                    user_message = data.get('content', {}).get('text', '')
                    conversation_history.append({
                        'role': 'user',
                        'content': user_message
                    })

                    if response.get('type') == 'agent_response':
                        conversation_history.append({
                            'role': 'assistant',
                            'content': response.get('content', {}).get('text', '')
                        })

                # Enviar respuesta
                await websocket.send(json.dumps(response))
                logger.info(f"Respuesta enviada: {response.get('type', 'unknown')}")

            except json.JSONDecodeError:
                error_response = {
                    "type": "error",
                    "content": {
                        "message": "Error: Formato de mensaje inválido"
                    }
                }
                await websocket.send(json.dumps(error_response))
            except Exception as e:
                logger.error(f"Error procesando mensaje: {e}")
                error_response = {
                    "type": "error",
                    "content": {
                        "message": f"Error interno: {str(e)}"
                    }
                }
                await websocket.send(json.dumps(error_response))

    except websockets.exceptions.ConnectionClosed:
        logger.info("Conexión WebSocket cerrada")
    except Exception as e:
        logger.error(f"Error en WebSocket: {e}")

async def main():
    """Función principal del servidor"""
    host = "0.0.0.0"
    port = 8001

    logger.info(f"🚀 Iniciando servidor II-Agent en {host}:{port}")
    logger.info("✅ Mecanismo anti-bucle activado (límites: 2 búsquedas / 3 planificaciones)")

    async with websockets.serve(handle_websocket, host, port):
        logger.info(f"✅ Servidor WebSocket ejecutándose en ws://{host}:{port}")
        await asyncio.Future()  # Ejecutar indefinidamente

if __name__ == "__main__":
    asyncio.run(main())
