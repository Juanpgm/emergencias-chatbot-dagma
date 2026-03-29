# Seguridad — Reglas globales

- Nunca loguear API keys, tokens ni datos sensibles del usuario.
- Validar todos los inputs en la capa de router con Pydantic/Form.
- Sanitizar antes de insertar en DB (SQLAlchemy parametriza automáticamente).
- No exponer stack traces al usuario; retornar mensajes genéricos en HTTPException.
- Usar HTTPS en producción para el webhook.
- Verificar token del webhook antes de procesar mensajes.
- No ejecutar comandos del sistema basados en entrada del usuario.
- Archivos temporales: limpiar siempre en bloque finally.
