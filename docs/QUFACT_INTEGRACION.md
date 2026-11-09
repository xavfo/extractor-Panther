# Integración de facturación con QuFact

## Por qué un endpoint nuevo y no el que ya existe

QuFact autentica su interfaz y sus endpoints (`api_facturas.php`, `api.php`, …)
con **sesión PHP** (`include/auth.php`). El visor es otro sistema, en otro
lenguaje y otro proceso: no comparte esa sesión.

El endpoint `api.php` sí acepta sistemas externos, pero exige **el XML del SRI ya
firmado**, y el visor no tiene certificado ni debe firmar documentos fiscales.
Por eso se propone un endpoint JSON con token, donde QuFact sigue siendo el dueño
de la numeración, el IVA, la firma, el envío al SRI y el RIDE.

## Contrato propuesto

### `POST {QUFACT_URL}/api/visor/emitir.php`

Cabeceras:

```
Authorization: Bearer <QUFACT_TOKEN>
Content-Type: application/json
Accept: application/json
```

Cuerpo:

```json
{
  "ruc": "1791234567001",
  "custom_uid": "panther:1234",
  "cliente": {
    "tipo_identificacion": "05",
    "identificacion": "1712345678",
    "razon_social": "MARÍA PAZMIÑO",
    "telefono": "0991476060",
    "email": "fer_paz2007@hotmail.com",
    "direccion": "TUMBACO"
  },
  "items": [
    {
      "descripcion": "CONSULTA",
      "cantidad": 1,
      "precio_unitario": 25.00,
      "codigo": "CONSULTA",
      "iva_porcentaje": 15
    }
  ],
  "forma_pago": "01",
  "observaciones": "Emitido desde VetVisor · movimiento Panther 1234",
  "referencia": {
    "sistema": "vetvisor",
    "iCodPaciente": "757214775238223947664195584",
    "iCodCuentaCliente": "1234"
  }
}
```

Campos obligatorios: `ruc`, `custom_uid`, `cliente.identificacion`,
`cliente.razon_social`, `items` (al menos uno).

- `custom_uid` es la **clave de idempotencia**. Si llega dos veces, QuFact
  devuelve el comprobante ya emitido y `reutilizado: true`; nunca emite dos
  facturas por el mismo movimiento.
- `forma_pago` usa los códigos del SRI (`01` efectivo, `19` tarjeta de crédito,
  `20` otros). Si el visor no lo envía, QuFact usa el medio de pago por defecto
  del contribuyente.
- `iva_porcentaje` es opcional: si falta, QuFact aplica el IVA del producto
  (`api_products`) o la tarifa general vigente. **El visor no decide impuestos.**
- `cliente.tipo_identificacion` sigue la tabla del SRI (`04` RUC, `05` cédula,
  `06` pasaporte, `07` consumidor final).

Respuesta correcta:

```json
{
  "success": true,
  "message": "Comprobante emitido",
  "clave_acceso": "0911202601179123456700110010010000001231234567812",
  "estado": "PPR",
  "numero_autorizacion": null,
  "custom_uid": "panther:1234",
  "reutilizado": false
}
```

Respuesta de error (siempre `success: false` y código HTTP coherente):

| HTTP | Cuándo |
| --- | --- |
| 400 | Datos incompletos o ítems inválidos |
| 401 | Token ausente o inválido |
| 403 | El token no pertenece al RUC solicitado |
| 409 | El contribuyente está inactivo o sin certificado vigente |
| 502 | El SRI no respondió; se puede reintentar con el mismo `custom_uid` |

## Mapa Panther → QuFact

| Panther | QuFact |
| --- | --- |
| `TranCuentasClientes.iCodCuentaCliente` | `custom_uid` (`panther:{id}`) |
| `TranCuentasClientes.vchServicio` | `items[].descripcion` |
| `TranCuentasClientes.dCantidad` | `items[].cantidad` |
| `TranCuentasClientes.dPrecioMenudeo` | `items[].precio_unitario` |
| `TranCuentasClientes.iCodProducto` / `iCodServicio` | `items[].codigo` (para conciliar con el catálogo de QuFact) |
| `TranAfiliado.vchRFC` | `cliente.identificacion` |
| `TranAfiliado` (nombre, teléfono, correo, dirección) | `cliente` |
| `TranAbonosCuentasClientes.iCodTipoPago` | `forma_pago` (con tabla de equivalencias) |

El RUC del emisor (`CatEmpresas.vchRFC` o configuración del visor) identifica al
contribuyente en QuFact; el token debe estar limitado a ese contribuyente.

## Seguridad en QuFact

1. El token se guarda **hasheado** en una tabla nueva (`tokens_sistema`) con
   `contrib_id`, descripción, estado y último uso.
2. Cada petición se registra en `auditoria` (o en el log `pagos`) con IP, RUC,
   `custom_uid` y resultado.
3. Límite de peticiones por token (por ejemplo 60 por minuto).
4. El endpoint no permite anular, cambiar datos del contribuyente ni consultar
   comprobantes de otros RUC.
5. Migración idempotente en `sql/migrations/NNN_tokens_sistema.sql`, reflejada en
   `sql/esquema/` y en `sql/deploy.sql` (convención del repositorio qfact).

## Pasos de implementación en el repositorio qfact

1. Migración `tokens_sistema` y alta manual del token del visor.
2. `public/api_visor.php` con `action=emitir` (misma forma `{success, message, …}`).
3. Reutilizar `ComprobanteService` para crear el comprobante en estado `PPR`, igual
   que `api.php`, y dejar que `CronRetry` complete la autorización.
4. Extender `tools/verificar_api.php` con los casos: token inválido, RUC ajeno,
   emisión correcta y reintento con el mismo `custom_uid`.
5. No tocar la base de producción ni desplegar sin autorización expresa.

## Verificación del lado del visor

```powershell
# Con QUFACT_URL y QUFACT_TOKEN en .env
.\.venv\Scripts\python.exe -c "from app import qufact; print(qufact.disponible())"
```

La emisión real se probará contra el servidor de desarrollo de QuFact
(`php -S 127.0.0.1:8099 -t .`), nunca contra el SRI de producción.
