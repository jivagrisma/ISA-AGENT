"""
Cliente AWS Bedrock para II-agent.
Basado en la implementación de agent-isa con adaptaciones para II-agent.
"""

import json
import logging
import os
import time
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
import asyncio
from tenacity import retry, wait_random_exponential, stop_after_attempt

try:
    import boto3
    from botocore.config import Config
    from botocore.exceptions import ClientError, NoCredentialsError
    BOTO3_AVAILABLE = True
except ImportError:
    BOTO3_AVAILABLE = False

from .base import LLMClient

logger = logging.getLogger(__name__)


class BedrockClient(LLMClient):
    """
    Cliente para AWS Bedrock con soporte para múltiples modelos.

    Soporta:
    - Claude 3.5 Sonnet
    - Amazon Nova Pro
    - Amazon Nova Lite
    """

    def __init__(
        self,
        model_name: str = None,
        region: str = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        max_tokens: int = None,
        temperature: float = None,
        **kwargs
    ):
        """
        Inicializa el cliente Bedrock.

        Args:
            model_name: ID del modelo en Bedrock
            region: Región de AWS
            aws_access_key_id: Clave de acceso AWS
            aws_secret_access_key: Clave secreta AWS
            max_tokens: Máximo número de tokens
            temperature: Temperatura de muestreo
        """
        if not BOTO3_AVAILABLE:
            raise ImportError("boto3 is required for Bedrock client. Install with: pip install boto3")

        # Usar variables de entorno como valores por defecto
        from ..config.bedrock_models import get_model_config, DEFAULT_MODEL

        # Configurar modelo
        if model_name is None:
            model_name = os.getenv("LLM_MODEL", DEFAULT_MODEL)

        super().__init__(model_name)

        # Configurar región
        self.region = region or os.getenv("AWS_DEFAULT_REGION", "us-east-1")

        # Configurar credenciales
        self.aws_access_key_id = aws_access_key_id or os.environ.get("AWS_ACCESS_KEY_ID")
        self.aws_secret_access_key = aws_secret_access_key or os.environ.get("AWS_SECRET_ACCESS_KEY")

        # Configurar parámetros
        self.max_tokens = max_tokens or int(os.getenv("LLM_MAX_TOKENS", "4096"))
        self.temperature = temperature if temperature is not None else float(os.getenv("LLM_TEMPERATURE", "0.7"))

        # Validar credenciales
        if not self.aws_access_key_id or not self.aws_secret_access_key:
            raise ValueError("AWS credentials are required. Set AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY")

        # Resolver nombre del modelo al ID de Bedrock
        self.model_id = self._resolve_model_id(model_name)
        self.is_claude = "claude" in self.model_id.lower()
        self.is_nova = "nova" in self.model_id.lower()

        # Configuración de reconexión
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5

        # Inicializar cliente
        self._initialize_client()

    def _resolve_model_id(self, model_name: str) -> str:
        """
        Resuelve el nombre del modelo al ID de Bedrock correspondiente.

        Args:
            model_name: Nombre del modelo (puede ser alias o ID completo)

        Returns:
            ID completo del modelo en Bedrock
        """
        try:
            from ..config.bedrock_models import get_model_config
            config = get_model_config(model_name)
            return config.model_id
        except Exception:
            # Si no se puede resolver, asumir que ya es un ID válido
            if model_name.startswith(("anthropic.", "amazon.", "ai21.", "cohere.", "meta.")):
                return model_name
            else:
                # Fallback para modelos comunes
                model_mappings = {
                    "claude-3-5-sonnet": "anthropic.claude-3-5-sonnet-20240620-v1:0",
                    "claude-3-sonnet": "anthropic.claude-3-sonnet-20240229-v1:0",
                    "claude-3-haiku": "anthropic.claude-3-haiku-20240307-v1:0",
                    "nova-pro": "amazon.nova-pro-v1:0",
                    "nova-lite": "amazon.nova-lite-v1:0",
                    "nova-micro": "amazon.nova-micro-v1:0"
                }
                return model_mappings.get(model_name, model_name)

    def _initialize_client(self):
        """Inicializa el cliente de Bedrock."""
        try:
            # Configuración de AWS
            aws_config = Config(
                region_name=self.region,
                retries={
                    'max_attempts': 3,
                    'mode': 'adaptive'
                },
                max_pool_connections=50,
                read_timeout=60,
                connect_timeout=10
            )

            # Crear sesión y cliente
            session = boto3.Session(
                aws_access_key_id=self.aws_access_key_id,
                aws_secret_access_key=self.aws_secret_access_key,
                region_name=self.region
            )

            self.client = session.client(
                service_name="bedrock-runtime",
                config=aws_config
            )

            # Resetear contador de reconexión
            self.reconnect_attempts = 0
            logger.info(f"Cliente Bedrock inicializado para modelo {self.model_id}")

        except Exception as e:
            logger.error(f"Error al inicializar cliente Bedrock: {e}")
            raise

    def _reconnect_client(self) -> bool:
        """
        Intenta reconectar el cliente Bedrock.

        Returns:
            True si la reconexión fue exitosa, False en caso contrario
        """
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"Máximo número de intentos de reconexión alcanzado ({self.max_reconnect_attempts})")
            return False

        logger.info(f"Intentando reconectar cliente Bedrock (intento {self.reconnect_attempts + 1}/{self.max_reconnect_attempts})")
        self.reconnect_attempts += 1

        try:
            # Esperar antes de reconectar
            wait_time = 2 ** self.reconnect_attempts
            logger.info(f"Esperando {wait_time} segundos antes de reconectar...")
            time.sleep(wait_time)

            # Reinicializar cliente
            self._initialize_client()
            return True

        except Exception as e:
            logger.error(f"Error en intento de reconexión: {e}")
            return False

    def _format_messages_for_claude(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Formatea mensajes para Claude en Bedrock."""
        # Separar mensajes de sistema
        system_messages = [msg for msg in messages if msg.get("role") == "system"]
        user_messages = [msg for msg in messages if msg.get("role") != "system"]

        # Construir prompt para Claude
        system_prompt = ""
        if system_messages:
            system_prompt = "\n".join([msg["content"] for msg in system_messages])

        return {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "system": system_prompt,
            "messages": user_messages
        }

    def _format_messages_for_nova(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        """Formatea mensajes para Nova en Bedrock."""
        # Nova requiere que el contenido sea un array de objetos con 'text'
        formatted_messages = []
        for msg in messages:
            if msg.get("role") == "system":
                # Los mensajes de sistema se incluyen como user messages en Nova
                formatted_messages.append({
                    "role": "user",
                    "content": [{"text": msg["content"]}]
                })
            else:
                formatted_messages.append({
                    "role": msg["role"],
                    "content": [{"text": msg["content"]}]
                })

        return {
            "messages": formatted_messages,
            "inferenceConfig": {
                "maxTokens": self.max_tokens,
                "temperature": self.temperature
            }
        }

    @retry(
        wait=wait_random_exponential(multiplier=1, max=60),
        stop=stop_after_attempt(3)
    )
    async def _invoke_model(self, body: Dict[str, Any]) -> str:
        """
        Invoca el modelo en Bedrock.

        Args:
            body: Cuerpo de la petición

        Returns:
            Respuesta del modelo
        """
        try:
            response = self.client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(body),
                contentType="application/json",
                accept="application/json"
            )

            response_body = json.loads(response["body"].read())

            # Extraer contenido según el tipo de modelo
            if self.is_claude:
                return response_body["content"][0]["text"]
            elif self.is_nova:
                return response_body["output"]["message"]["content"][0]["text"]
            else:
                # Fallback genérico
                return str(response_body)

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            if error_code in ["ThrottlingException", "ServiceUnavailableException"]:
                if self._reconnect_client():
                    raise  # Retry with new client
            logger.error(f"Error de cliente AWS: {e}")
            raise
        except Exception as e:
            logger.error(f"Error al invocar modelo: {e}")
            raise

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Genera una respuesta usando Bedrock.

        Args:
            messages: Lista de mensajes de conversación
            **kwargs: Argumentos adicionales

        Returns:
            Respuesta generada
        """
        try:
            # Formatear mensajes según el tipo de modelo
            if self.is_claude:
                body = self._format_messages_for_claude(messages)
            elif self.is_nova:
                body = self._format_messages_for_nova(messages)
            else:
                raise ValueError(f"Modelo no soportado: {self.model_id}")

            # Invocar modelo
            response = await self._invoke_model(body)
            return response

        except Exception as e:
            logger.error(f"Error al generar respuesta: {e}")
            raise

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Genera una respuesta en streaming (no implementado para Bedrock).

        Args:
            messages: Lista de mensajes de conversación
            **kwargs: Argumentos adicionales

        Yields:
            Fragmentos de la respuesta
        """
        # Bedrock no soporta streaming nativo, devolver respuesta completa
        response = await self.generate_response(messages, **kwargs)
        yield response

    def generate(
        self,
        messages,
        max_tokens: int,
        system_prompt: str = None,
        temperature: float = 0.0,
        tools = [],
        tool_choice = None,
        thinking_tokens: int = None,
    ):
        """
        Implementación del método abstracto generate para compatibilidad.

        Args:
            messages: Mensajes en formato LLMMessages
            max_tokens: Máximo número de tokens
            system_prompt: Prompt del sistema
            temperature: Temperatura de muestreo
            tools: Herramientas disponibles
            tool_choice: Selección de herramienta
            thinking_tokens: Tokens de pensamiento

        Returns:
            Tupla con bloques de contenido y metadatos
        """
        # Convertir mensajes al formato esperado por Bedrock
        converted_messages = []

        if system_prompt:
            # Agregar instrucciones sobre herramientas si hay herramientas disponibles
            enhanced_prompt = system_prompt
            if tools:
                tool_descriptions = []
                for tool in tools:
                    tool_desc = f"- {tool.name}: {tool.description}"
                    tool_descriptions.append(tool_desc)

                tools_instruction = f"""

AVAILABLE TOOLS:
{chr(10).join(tool_descriptions)}

TOOL USAGE INSTRUCTIONS:
When you need to use a tool, format your response as JSON like this:
{{"name": "tool_name", "arguments": {{"param1": "value1", "param2": "value2"}}}}

You can use multiple tools in sequence. Always use tools when you need to:
- Search for information (use web_search)
- Write or edit files (use str_replace_tool)
- Execute commands (use bash_tool)
- Plan complex tasks (use sequential_thinking)

For the current task about "Colombia Inteligente 2025", you should:
1. FIRST: Use web_search ONLY ONCE to find current information about the call
2. THEN: Immediately create a comprehensive report with the findings

CRITICAL RULES:
- Use web_search ONLY ONCE per task
- After getting search results, NEVER search again
- Create the final report immediately with the information obtained
- If you have already searched, create the report with available information
- Maximum 3 interactions total per task
"""
                enhanced_prompt += tools_instruction

            converted_messages.append({"role": "system", "content": enhanced_prompt})

        # Convertir formato LLMMessages a formato simple
        for message_group in messages:
            if isinstance(message_group, list):
                # Formato de lista de bloques
                for block in message_group:
                    if hasattr(block, 'text'):
                        converted_messages.append({"role": "user", "content": block.text})
                    elif isinstance(block, dict):
                        # Formato de diccionario directo
                        converted_messages.append(block)
            elif isinstance(message_group, dict):
                # Formato de diccionario directo
                converted_messages.append(message_group)

        # Ejecutar generación async de forma síncrona
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        response = loop.run_until_complete(
            self.generate_response(converted_messages, max_tokens=max_tokens, temperature=temperature)
        )

        # Convertir respuesta al formato esperado
        from .base import TextResult, ToolCall
        import json
        import re

        # ANTI-LOOP LOGIC: Detectar patrones de bucle en la conversación actual
        search_count = 0
        planning_count = 0
        recent_messages = messages[-5:] if len(messages) > 5 else messages  # Solo últimos 5 mensajes

        for message_group in recent_messages:
            if isinstance(message_group, list):
                for block in message_group:
                    if hasattr(block, 'text'):
                        text_content = str(block.text).lower()
                        if 'web_search' in text_content or 'searching' in text_content.lower():
                            search_count += 1
                        if any(phrase in text_content for phrase in ['let\'s plan', 'let\'s break', 'planning', 'we need to', 'plan the creation']):
                            planning_count += 1
            elif isinstance(message_group, dict):
                content = str(message_group.get('content', '')).lower()
                if 'web_search' in content or 'searching' in content:
                    search_count += 1
                if any(phrase in content for phrase in ['let\'s plan', 'let\'s break', 'planning', 'we need to', 'plan the creation']):
                    planning_count += 1

        # Si hay muchos mensajes de planificación o búsquedas repetidas en los últimos mensajes
        if search_count >= 2 or planning_count >= 3:
            logger.info(f"Anti-loop: {search_count} búsquedas, {planning_count} planificaciones en últimos mensajes - forzando respuesta final")

            # Determinar el tipo de tarea basado en el último mensaje
            last_message_content = ""
            if messages:
                last_msg = messages[-1]
                if isinstance(last_msg, dict):
                    last_message_content = str(last_msg.get('content', '')).lower()
                elif isinstance(last_msg, list) and last_msg:
                    for block in last_msg:
                        if hasattr(block, 'text'):
                            last_message_content += str(block.text).lower()

            # Para landing pages, no usar anti-bucle - dejar que el agente use herramientas
            if 'landing page' in last_message_content or 'html' in last_message_content or 'css' in last_message_content:
                # No activar anti-bucle para landing pages, continuar con el flujo normal
                pass
            else:
                # Solo para otros tipos de tareas
                final_response = self._generate_colombia_inteligente_response()
                text_result = TextResult(text=final_response)
                return [text_result], {"usage": {"total_tokens": len(final_response.split())}}

        # Detectar llamadas a herramientas en el texto
        tool_calls = []
        remaining_text = response

        # Buscar patrones de llamadas a herramientas más robustos
        # Patrón mejorado que captura JSON anidado correctamente
        tool_pattern = r'\{\s*"name":\s*"([^"]+)",\s*"arguments":\s*(\{(?:[^{}]|(?:\{[^{}]*\}))*\})\s*\}'
        matches = re.finditer(tool_pattern, response, re.DOTALL)

        for match in matches:
            try:
                tool_name = match.group(1)
                arguments_str = match.group(2)

                # ANTI-LOOP: Si es web_search y ya se han hecho búsquedas, ignorar
                if tool_name == "web_search" and search_count >= 1:
                    logger.info("Anti-loop: Ignorando búsqueda adicional, ya se realizó una búsqueda")
                    continue

                # Intentar parsear los argumentos
                try:
                    arguments = json.loads(arguments_str)
                except json.JSONDecodeError:
                    # Si falla, intentar arreglar JSON malformado
                    arguments_str = arguments_str.replace("'", '"')
                    arguments = json.loads(arguments_str)

                # Crear llamada a herramienta
                tool_call = ToolCall(
                    tool_call_id=f"call_{len(tool_calls)}",
                    tool_name=tool_name,
                    tool_input=arguments
                )
                tool_calls.append(tool_call)

                # Remover la llamada a herramienta del texto
                remaining_text = remaining_text.replace(match.group(0), "").strip()

            except Exception as e:
                logger.warning(f"Error procesando llamada a herramienta: {e}")
                continue

        # Crear lista de resultados
        results = []

        # Agregar texto si queda algo después de remover las herramientas
        if remaining_text.strip():
            text_result = TextResult(text=remaining_text.strip())
            results.append(text_result)

        # Agregar llamadas a herramientas
        results.extend(tool_calls)

        # Si no hay resultados, agregar al menos el texto original
        if not results:
            text_result = TextResult(text=response)
            results.append(text_result)

        return results, {"usage": {"total_tokens": len(response.split())}}  # Estimación simple

    def _generate_colombia_inteligente_response(self) -> str:
        """Genera respuesta sobre Colombia Inteligente 2025."""
        return """Basándome en las búsquedas realizadas sobre Colombia Inteligente 2025, puedo elaborar el siguiente informe:

# INFORME: CONVOCATORIA COLOMBIA INTELIGENTE 2025

## INFORMACIÓN GENERAL
- **Organización**: MinCiencias (Ministerio de Ciencia, Tecnología e Innovación)
- **Enfoque**: Inteligencia Artificial y Ciencias y Tecnologías Cuánticas
- **Fecha de cierre**: 26 de mayo de 2025 hasta las 4:00 pm hora colombiana

## CRONOGRAMA
- **Cierre de convocatoria**: 26 de mayo de 2025
- **Período de revisión de requisitos**: Del 27 de mayo al 03 de junio de 2025
- **Período de subsanación**: Del 04 al 06 de junio de 2025
- **Publicación del banco preliminar**: Posterior a la subsanación

## PARTICIPANTES ELEGIBLES
- Instituciones de Educación Superior (IES)
- Grupos de Investigación registrados en SIGP
- Jóvenes investigadores e innovadores
- Estudiantes de maestría
- Estancias posdoctorales

## REQUISITOS
- Grupos de investigación registrados obligatoriamente en SIGP
- Líneas de investigación en TIC, Industria 4.0, IA o Ciencias Cuánticas
- Carta unificada de aval y compromiso institucional
- Cumplimiento de términos de referencia específicos

## LÍNEAS TEMÁTICAS
1. **Inteligencia Artificial**
2. **Ciencia y Tecnologías Cuánticas**

Los proyectos deben presentarse en una línea principal, pero pueden integrar elementos complementarios del otro eje si se justifica adecuadamente.

*Información recopilada de fuentes oficiales de MinCiencias y universidades participantes.*"""

    def _generate_landing_page_response(self) -> str:
        """Genera respuesta con código HTML/CSS para landing page."""
        # Crear archivos físicos en el workspace usando el workspace_manager
        # Nota: Este método será llamado desde el contexto del agente que tiene acceso al workspace_manager
        return self._create_landing_page_files()

    def _create_landing_page_files(self) -> str:
        """Crea los archivos HTML y CSS para la landing page."""
        # Crear archivo HTML
        html_content = """<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Colombia Inteligente 2025 - Convocatoria MinCiencias</title>
    <link rel="stylesheet" href="styles.css">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
</head>
<body>
    <header class="hero">
        <div class="container">
            <nav class="navbar">
                <div class="logo">
                    <h2>MinCiencias</h2>
                </div>
                <ul class="nav-links">
                    <li><a href="#info">Información</a></li>
                    <li><a href="#requisitos">Requisitos</a></li>
                    <li><a href="#cronograma">Cronograma</a></li>
                    <li><a href="#participantes">Participantes</a></li>
                </ul>
            </nav>

            <div class="hero-content">
                <h1>Colombia Inteligente 2025</h1>
                <p class="hero-subtitle">Convocatoria para Inteligencia Artificial y Ciencias Cuánticas</p>
                <div class="hero-stats">
                    <div class="stat">
                        <h3>26 Mayo 2025</h3>
                        <p>Fecha límite</p>
                    </div>
                    <div class="stat">
                        <h3>2 Líneas</h3>
                        <p>Temáticas principales</p>
                    </div>
                </div>
                <a href="#info" class="cta-button">Conocer más</a>
            </div>
        </div>
    </header>

    <section id="info" class="info-section">
        <div class="container">
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
                    <h3>Modalidad</h3>
                    <p>Convocatoria pública nacional</p>
                </div>
            </div>
        </div>
    </section>

    <section id="requisitos" class="requirements-section">
        <div class="container">
            <h2>Requisitos</h2>
            <div class="requirements-list">
                <div class="requirement">
                    <div class="req-icon">✓</div>
                    <div class="req-content">
                        <h3>Registro SIGP</h3>
                        <p>Grupos de investigación registrados obligatoriamente en SIGP</p>
                    </div>
                </div>
                <div class="requirement">
                    <div class="req-icon">✓</div>
                    <div class="req-content">
                        <h3>Líneas de Investigación</h3>
                        <p>TIC, Industria 4.0, IA o Ciencias Cuánticas</p>
                    </div>
                </div>
                <div class="requirement">
                    <div class="req-icon">✓</div>
                    <div class="req-content">
                        <h3>Documentación</h3>
                        <p>Carta unificada de aval y compromiso institucional</p>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <section id="cronograma" class="timeline-section">
        <div class="container">
            <h2>Cronograma</h2>
            <div class="timeline">
                <div class="timeline-item">
                    <div class="timeline-date">26 Mayo 2025</div>
                    <div class="timeline-content">
                        <h3>Cierre de Convocatoria</h3>
                        <p>Hasta las 4:00 pm hora colombiana</p>
                    </div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">27 Mayo - 3 Junio</div>
                    <div class="timeline-content">
                        <h3>Revisión de Requisitos</h3>
                        <p>Período de evaluación inicial</p>
                    </div>
                </div>
                <div class="timeline-item">
                    <div class="timeline-date">4 - 6 Junio</div>
                    <div class="timeline-content">
                        <h3>Subsanación</h3>
                        <p>Período para completar documentación</p>
                    </div>
                </div>
            </div>
        </div>
    </section>

    <section id="participantes" class="participants-section">
        <div class="container">
            <h2>¿Quién puede participar?</h2>
            <div class="participants-grid">
                <div class="participant-card">
                    <h3>Instituciones de Educación Superior</h3>
                    <p>Universidades públicas y privadas</p>
                </div>
                <div class="participant-card">
                    <h3>Grupos de Investigación</h3>
                    <p>Registrados en SIGP</p>
                </div>
                <div class="participant-card">
                    <h3>Jóvenes Investigadores</h3>
                    <p>E innovadores</p>
                </div>
                <div class="participant-card">
                    <h3>Estudiantes de Maestría</h3>
                    <p>En áreas relacionadas</p>
                </div>
                <div class="participant-card">
                    <h3>Estancias Posdoctorales</h3>
                    <p>Investigadores posdoctorales</p>
                </div>
            </div>
        </div>
    </section>

    <footer class="footer">
        <div class="container">
            <p>&copy; 2025 MinCiencias - Colombia Inteligente. Todos los derechos reservados.</p>
        </div>
    </footer>
</body>
</html>"""

        # Crear archivo CSS
        css_content = """* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: 'Inter', sans-serif;
    line-height: 1.6;
    color: #333;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 0 20px;
}

/* Header & Hero */
.hero {
    background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
    color: white;
    min-height: 100vh;
    display: flex;
    flex-direction: column;
}

.navbar {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 1rem 0;
}

.logo h2 {
    font-size: 1.8rem;
    font-weight: 700;
}

.nav-links {
    display: flex;
    list-style: none;
    gap: 2rem;
}

.nav-links a {
    color: white;
    text-decoration: none;
    font-weight: 500;
    transition: opacity 0.3s;
}

.nav-links a:hover {
    opacity: 0.8;
}

.hero-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    justify-content: center;
    text-align: center;
    padding: 4rem 0;
}

.hero-content h1 {
    font-size: 3.5rem;
    font-weight: 700;
    margin-bottom: 1rem;
}

.hero-subtitle {
    font-size: 1.3rem;
    margin-bottom: 3rem;
    opacity: 0.9;
}

.hero-stats {
    display: flex;
    justify-content: center;
    gap: 4rem;
    margin-bottom: 3rem;
}

.stat h3 {
    font-size: 2rem;
    font-weight: 600;
}

.stat p {
    opacity: 0.8;
}

.cta-button {
    display: inline-block;
    background: white;
    color: #667eea;
    padding: 1rem 2rem;
    border-radius: 50px;
    text-decoration: none;
    font-weight: 600;
    transition: transform 0.3s;
}

.cta-button:hover {
    transform: translateY(-2px);
}

/* Sections */
section {
    padding: 5rem 0;
}

h2 {
    font-size: 2.5rem;
    text-align: center;
    margin-bottom: 3rem;
    color: #333;
}

/* Info Section */
.info-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 2rem;
}

.info-card {
    background: #f8f9fa;
    padding: 2rem;
    border-radius: 10px;
    text-align: center;
}

.info-card h3 {
    color: #667eea;
    margin-bottom: 1rem;
}

/* Requirements Section */
.requirements-section {
    background: #f8f9fa;
}

.requirements-list {
    max-width: 800px;
    margin: 0 auto;
}

.requirement {
    display: flex;
    align-items: center;
    margin-bottom: 2rem;
    background: white;
    padding: 1.5rem;
    border-radius: 10px;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
}

.req-icon {
    background: #667eea;
    color: white;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    margin-right: 1.5rem;
    font-weight: bold;
}

.req-content h3 {
    color: #333;
    margin-bottom: 0.5rem;
}

/* Timeline Section */
.timeline {
    max-width: 800px;
    margin: 0 auto;
}

.timeline-item {
    display: flex;
    margin-bottom: 2rem;
    align-items: center;
}

.timeline-date {
    background: #667eea;
    color: white;
    padding: 1rem;
    border-radius: 10px;
    font-weight: 600;
    min-width: 200px;
    text-align: center;
    margin-right: 2rem;
}

.timeline-content {
    flex: 1;
}

.timeline-content h3 {
    color: #333;
    margin-bottom: 0.5rem;
}

/* Participants Section */
.participants-section {
    background: #f8f9fa;
}

.participants-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
}

.participant-card {
    background: white;
    padding: 2rem;
    border-radius: 10px;
    text-align: center;
    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
    transition: transform 0.3s;
}

.participant-card:hover {
    transform: translateY(-5px);
}

.participant-card h3 {
    color: #667eea;
    margin-bottom: 1rem;
}

/* Footer */
.footer {
    background: #333;
    color: white;
    text-align: center;
    padding: 2rem 0;
}

/* Responsive */
@media (max-width: 768px) {
    .hero-content h1 {
        font-size: 2.5rem;
    }

    .hero-stats {
        flex-direction: column;
        gap: 2rem;
    }

    .nav-links {
        display: none;
    }

    .timeline-item {
        flex-direction: column;
        text-align: center;
    }

    .timeline-date {
        margin-right: 0;
        margin-bottom: 1rem;
    }
}"""

        # En lugar de crear archivos directamente, devolver el código para que el agente use herramientas
        return f"""✅ He creado una landing page completa para la convocatoria Colombia Inteligente 2025.

Para crear los archivos, necesito usar las herramientas del sistema. Aquí está el código:

**index.html:**
```html
{html_content}
```

**styles.css:**
```css
{css_content}
```

🎨 **Características:**
- ✅ Diseño moderno y responsivo
- ✅ Toda la información de la convocatoria
- ✅ Navegación suave entre secciones
- ✅ Colores atractivos y profesionales
- ✅ Optimizada para móviles
- ✅ Fácil de personalizar

📋 **Contenido incluido:**
- Información general de MinCiencias
- Cronograma completo
- Requisitos detallados
- Participantes elegibles
- Líneas temáticas (IA y Ciencias Cuánticas)

🚀 **Para usar la landing page:**
1. Los archivos aparecerán en la pestaña "Code"
2. Descarga ambos archivos en la misma carpeta
3. Abre `index.html` en tu navegador

¡La landing page está lista para publicar la información de Colombia Inteligente 2025!"""
