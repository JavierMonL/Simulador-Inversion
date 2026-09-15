import io
import re
from pathlib import Path
from datetime import date
from urllib.parse import quote

import pandas as pd
import streamlit as st
from dateutil.relativedelta import relativedelta
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image

st.set_page_config(page_title="Simulador de Inversión | VaZentica", page_icon="📈", layout="centered")

BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "Logo Capital.png"


# ============================================================
# ACCESO RESTRINGIDO CON GOOGLE
# ============================================================

def validar_acceso():
    """Solicita inicio de sesión y permite acceso solo a correos autorizados."""
    if not st.user.is_logged_in:
        st.title("🔐 Acceso restringido")
        st.write("Inicia sesión con tu cuenta de Google autorizada para utilizar el simulador.")
        st.button("Continuar con Google", on_click=st.login, use_container_width=True)
        st.stop()

    email = str(st.user.get("email", "")).strip().lower()
    usuarios_autorizados = {
        str(correo).strip().lower()
        for correo in st.secrets.get("acceso", {}).get("usuarios", [])
    }

    if not email or email not in usuarios_autorizados:
        st.error("Tu cuenta de Google no está autorizada para utilizar este simulador.")
        if email:
            st.caption(f"Cuenta identificada: {email}")
        st.button("Cerrar sesión", on_click=st.logout)
        st.stop()

    nombre = st.user.get("name", email)
    col_usuario, col_salida = st.columns([4, 1])
    with col_usuario:
        st.caption(f"Sesión iniciada: {nombre} · {email}")
    with col_salida:
        st.button("Cerrar sesión", on_click=st.logout, use_container_width=True)


validar_acceso()

TASAS = [
    (15_000, 200_000, {6: 0.09, 12: 0.11, 18: 0.13, 24: 0.14}),
    (200_001, 400_000, {6: 0.10, 12: 0.12, 18: 0.14, 24: 0.15}),
    (400_001, 600_000, {6: 0.11, 12: 0.13, 18: 0.15, 24: 0.16}),
    (600_001, 800_000, {6: 0.12, 12: 0.14, 18: 0.16, 24: 0.17}),
    (800_001, 1_000_000, {6: 0.13, 12: 0.15, 18: 0.17, 24: 0.18}),
    (1_000_001, float("inf"), {6: 0.14, 12: 0.16, 18: 0.18, 24: 0.19}),
]

def obtener_tasa(capital: float, plazo: int):
    if capital < 15_000:
        return None
    for desde, hasta, tasas_plazo in TASAS:
        if desde <= capital <= hasta:
            return tasas_plazo.get(plazo)
    return None

def generar_tabla_rendimientos(capital_inicial, plazo_meses, tasa_anual, fecha_inicio):
    tasa_mensual = tasa_anual / 12
    interes_mensual = capital_inicial * tasa_mensual
    filas = []
    for periodo in range(1, plazo_meses + 1):
        fecha_pago = fecha_inicio + relativedelta(months=periodo)
        capital_acumulado = capital_inicial + interes_mensual * periodo
        filas.append({
            "Periodo": periodo,
            "Fecha de pago": fecha_pago,
            "Interés generado": interes_mensual,
            "Capital acumulado": capital_acumulado,
        })
    return pd.DataFrame(filas)

def moneda(valor):
    return f"${valor:,.2f}"

def porcentaje(valor):
    return f"{valor * 100:,.2f}%"

def generar_pdf(prospecto, asesor, fecha_cotizacion, fecha_inicio, capital_inicial, plazo_meses, tasa_anual, tabla):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=18*mm, leftMargin=18*mm, topMargin=16*mm, bottomMargin=16*mm)
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="TituloVazentica", parent=styles["Title"], fontSize=18, leading=22, alignment=TA_CENTER, spaceAfter=8))
    styles.add(ParagraphStyle(name="Subtitulo", parent=styles["Heading2"], fontSize=11, leading=14, alignment=TA_CENTER, spaceAfter=12))
    styles.add(ParagraphStyle(name="Derecha", parent=styles["Normal"], alignment=TA_RIGHT, fontSize=8))
    styles.add(ParagraphStyle(name="Nota", parent=styles["Normal"], fontSize=7.5, leading=10, textColor=colors.HexColor("#444444")))

    tasa_mensual = tasa_anual / 12
    interes_mensual = capital_inicial * tasa_mensual
    rendimiento_total = interes_mensual * plazo_meses
    monto_vencimiento = capital_inicial + rendimiento_total
    fecha_vencimiento = fecha_inicio + relativedelta(months=plazo_meses)

    elementos = []

    # Logo discreto arriba a la izquierda y fecha arriba a la derecha.
    # El título se mantiene centrado e independiente del encabezado.
    if LOGO_PATH.exists():
        logo = Image(str(LOGO_PATH), width=30*mm, height=20*mm)
        encabezado = Table(
            [[logo, Paragraph(
                f"Fecha de simulación: {fecha_cotizacion.strftime('%d/%m/%Y')}",
                styles["Derecha"]
            )]],
            colWidths=[45*mm, 108*mm],
        )
        encabezado.setStyle(TableStyle([
            ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
            ("ALIGN", (0,0), (0,0), "LEFT"),
            ("ALIGN", (1,0), (1,0), "RIGHT"),
            ("BOTTOMPADDING", (0,0), (-1,-1), 2),
        ]))
        elementos.append(encabezado)
    else:
        elementos.append(
            Paragraph(
                f"Fecha de simulación: {fecha_cotizacion.strftime('%d/%m/%Y')}",
                styles["Derecha"]
            )
        )

    elementos += [
        Spacer(1, 2*mm),
        Paragraph("Simulación de Inversión", styles["TituloVazentica"]),
        Spacer(1, 3*mm),
    ]

    datos_cliente = [
        ["Prospecto", prospecto or "—"],
        ["Asesor", asesor or "—"],
        ["Fecha de inversión", fecha_inicio.strftime("%d/%m/%Y")],
        ["Fecha de vencimiento", fecha_vencimiento.strftime("%d/%m/%Y")],
    ]
    t_cliente = Table(datos_cliente, colWidths=[48*mm, 105*mm])
    t_cliente.setStyle(TableStyle([
        ("FONTNAME", (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 5),
        ("LINEBELOW", (0,0), (-1,-1), 0.25, colors.HexColor("#DDDDDD")),
    ]))
    elementos += [t_cliente, Spacer(1, 6*mm)]

    resumen = [
        ["Concepto", "Resultado"],
        ["Monto de inversión", moneda(capital_inicial)],
        ["Plazo", f"{plazo_meses} meses"],
        ["Tasa fija anual", porcentaje(tasa_anual)],
        ["Tasa mensual", porcentaje(tasa_mensual)],
        ["Rendimiento mensual", moneda(interes_mensual)],
        ["Rendimiento total", moneda(rendimiento_total)],
        ["Capital + rendimiento", moneda(monto_vencimiento)],
    ]
    t_resumen = Table(resumen, colWidths=[80*mm, 73*mm])
    t_resumen.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#EDEDED")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTNAME", (0,1), (0,-1), "Helvetica-Bold"),
        ("ALIGN", (1,1), (1,-1), "RIGHT"),
        ("FONTSIZE", (0,0), (-1,-1), 9),
        ("GRID", (0,0), (-1,-1), 0.35, colors.HexColor("#CCCCCC")),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("TOPPADDING", (0,0), (-1,-1), 5),
    ]))
    elementos += [t_resumen, Spacer(1, 7*mm), Paragraph("Tabla de rendimientos", styles["Heading3"]), Spacer(1, 2*mm)]

    tabla_pdf = [["Periodo", "Fecha de pago", "Interés generado", "Capital acumulado"]]
    for _, fila in tabla.iterrows():
        tabla_pdf.append([
            str(int(fila["Periodo"])),
            fila["Fecha de pago"].strftime("%d/%m/%Y"),
            moneda(float(fila["Interés generado"])),
            moneda(float(fila["Capital acumulado"])),
        ])
    t_detalle = Table(tabla_pdf, colWidths=[22*mm, 38*mm, 48*mm, 48*mm], repeatRows=1)
    estilo = [
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#EDEDED")),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("ALIGN", (0,0), (1,-1), "CENTER"),
        ("ALIGN", (2,1), (-1,-1), "RIGHT"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("GRID", (0,0), (-1,-1), 0.25, colors.HexColor("#D5D5D5")),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 4),
    ]
    for idx in range(1, len(tabla_pdf)):
        if idx % 2 == 0:
            estilo.append(("BACKGROUND", (0,idx), (-1,idx), colors.HexColor("#F4F4F4")))
    t_detalle.setStyle(TableStyle(estilo))
    elementos += [t_detalle, Spacer(1, 7*mm)]

    nota = ("La presente cotización es una simulación informativa basada en las condiciones vigentes al momento de su elaboración. "
            "Los resultados corresponden a un esquema de interés simple. La contratación definitiva se encuentra sujeta a la documentación, "
            "condiciones y autorizaciones aplicables.")
    elementos.append(Paragraph(nota, styles["Nota"]))
    doc.build(elementos)
    buffer.seek(0)
    return buffer.getvalue()

st.title("📈 Simulador de Inversión")
st.caption("Simulación de inversión con rendimiento simple.")

with st.form("form_simulacion"):
    st.subheader("Datos del prospecto")
    col1, col2 = st.columns(2)
    with col1:
        prospecto = st.text_input("Nombre del prospecto")
    with col2:
        asesor = st.text_input("Asesor / Promotor")

    st.subheader("Datos de la inversión")
    col3, col4 = st.columns(2)
    with col3:
        monto = st.number_input("Monto a invertir", min_value=15000.0, value=250000.0, step=5000.0, format="%.2f")
        fecha_inicio = st.date_input("Fecha de inversión", value=date.today())
    with col4:
        plazo = st.selectbox("Plazo", [6, 12, 18, 24], format_func=lambda x: f"{x} meses")
        st.text_input("Tipo de rendimiento", value="Simple", disabled=True)

    simular = st.form_submit_button("Calcular inversión", use_container_width=True)

if simular:
    tasa_anual = obtener_tasa(float(monto), int(plazo))
    if tasa_anual is None:
        st.error("No existe una tasa configurada para el monto y plazo seleccionados.")
        st.stop()

    tasa_mensual = tasa_anual / 12
    interes_mensual = float(monto) * tasa_mensual
    rendimiento_total = interes_mensual * int(plazo)
    monto_vencimiento = float(monto) + rendimiento_total
    fecha_vencimiento = fecha_inicio + relativedelta(months=int(plazo))

    tabla = generar_tabla_rendimientos(float(monto), int(plazo), tasa_anual, fecha_inicio)

    st.divider()
    st.subheader("Resultado de la simulación")
    c1, c2, c3 = st.columns(3)
    c1.metric("Tasa anual", porcentaje(tasa_anual))
    c2.metric("Tasa mensual", porcentaje(tasa_mensual))
    c3.metric("Rendimiento mensual", moneda(interes_mensual))

    c4, c5, c6 = st.columns(3)
    c4.metric("Rendimiento total", moneda(rendimiento_total))
    c5.metric("Capital + rendimiento", moneda(monto_vencimiento))
    c6.metric("Vencimiento", fecha_vencimiento.strftime("%d/%m/%Y"))

    st.subheader("Tabla de rendimientos")
    tabla_mostrar = tabla.copy()
    tabla_mostrar["Fecha de pago"] = tabla_mostrar["Fecha de pago"].apply(lambda x: x.strftime("%d/%m/%Y"))
    tabla_mostrar["Interés generado"] = tabla_mostrar["Interés generado"].apply(moneda)
    tabla_mostrar["Capital acumulado"] = tabla_mostrar["Capital acumulado"].apply(moneda)
    st.dataframe(tabla_mostrar, use_container_width=True, hide_index=True)

    pdf_bytes = generar_pdf(prospecto, asesor, date.today(), fecha_inicio, float(monto), int(plazo), tasa_anual, tabla)
    nombre_limpio = re.sub(r"[^A-Za-z0-9_-]+", "_", prospecto.strip()) if prospecto else "Prospecto"
    nombre_pdf = f"Simulacion_Inversion_{nombre_limpio}_{date.today().strftime('%Y%m%d')}.pdf"

    st.subheader("Cotización")
    b1, b2 = st.columns(2)
    with b1:
        st.download_button("📄 Descargar cotización PDF", data=pdf_bytes, file_name=nombre_pdf, mime="application/pdf", use_container_width=True)

    mensaje = (
        f"Hola {prospecto or ''}, te comparto tu simulación de inversión de VaZentica.\n\n"
        f"Monto de inversión: {moneda(float(monto))}\n"
        f"Plazo: {plazo} meses\n"
        f"Tasa fija anual: {porcentaje(tasa_anual)}\n"
        f"Rendimiento estimado: {moneda(rendimiento_total)}\n"
        f"Capital + rendimiento: {moneda(monto_vencimiento)}\n"
        f"Fecha de vencimiento: {fecha_vencimiento.strftime('%d/%m/%Y')}\n\n"
        "Te adjunto la cotización en PDF."
    )

    # No solicitamos ni almacenamos el teléfono del prospecto.
    # WhatsApp abre el selector de contacto con el mensaje precargado.
    url_whatsapp = f"https://wa.me/?text={quote(mensaje)}"

    with b2:
        st.link_button("💬 Abrir WhatsApp", url_whatsapp, use_container_width=True)

    st.info("El simulador no solicita el número del prospecto. WhatsApp abrirá el mensaje precargado; el asesor selecciona el contacto y adjunta manualmente el PDF.")
