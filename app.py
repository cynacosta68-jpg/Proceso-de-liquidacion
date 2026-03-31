
import streamlit as st
import fitz
import pandas as pd
import re
import os
import io
from datetime import datetime

# --- Helper Functions ---

def limpiar_monto_v14(t):
    if not t or t in ["-", ".", " - "]: return 0.0
    n = re.sub(r'[^\d\.,-]', '', str(t).strip()).replace('.', '').replace(',', '.')
    try: return float(n)
    except: return 0.0

def limpiar_importe_v91(texto):
    if not texto: return 0.0
    n = str(texto).replace(" ", "")
    n = re.sub(r'[^\d\.,-]', '', n).replace('.', '').replace(',', '.').strip()
    try:
        return float(n)
    except:
        return 0.0

def limpiar_num_deduc(texto):
    if not texto: return 0.0
    n = re.sub(r'[^\d\.,-]', '', str(texto)).replace('.', '').replace(',', '.').strip()
    try:
        return float(n)
    except:
        return 0.0

# --- Extraction Functions ---

def extraer_honorarios_v14(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    lineas = []
    for page in doc:
        raw = [l.strip() for l in page.get_text("text").split('\n') if l.strip()]
        k = 0
        while k < len(raw):
            if k+1 < len(raw) and re.match(r'^\d{1,2}$', raw[k+1]):
                lineas.append(raw[k] + raw[k+1]); k += 2
            else:
                lineas.append(raw[k]); k += 1
    doc.close()

    NOMBRES_OS = [
        "O.S.D.I.P.P.", "OSAPM DE LA R.A.", "CORTE SUPREMA DE JUSTICIA O. S. DEL PODER JUDICIAL",
        "SUPERINTENDENCIA DE BIENESTAR POLICIA FEDERAL ARG.", "S.E.R.O.S.", "O.S.P.I.A.",
        "GRIAL Salud SA", "O.S.DEL PERSONAL DE TELEVISION", "JERARQUICOS SALUD", "MEDICUS S.A.",
        "SWISS MEDICAL S.A.", "A.C.A. SALUD", "MEDIFE ASOCIACION CIVIL", "MEDIFE ASOCIACION CIVIL (I.V.A.)",
        "O.S.SEG.", "O.S.P.E.(Obra Social de Petroleros)", "GALENO Argentina S.A. AZUL/BLANCO/ORO/PLATA",
        "SCIS S.A. OSTRAC - AATRAC", "OBRA SOCIAL DE COND.CAMIONEROS", "CLINICA DEL VALLE SALUD S.R.L.",
        "O.S.P.I.L. (O.S.del Personal de la Ind. Lechera)", "O.S.D.O.P. (O.S.DOCENTES PARTICULARES)",
        "O.S.T.P.C.P.H.y A.R.A. (PASTELEROS)", "A.D.O.S.", "OBRA SOCIAL DE LUZ Y FUERZA DE LA PATAGONIA",
        "UNO SALUD S.A.", "ASOCIACION MUTUAL SANCOR", "ASOCIACION MUTUAL SANCOR - VOLUNTARIO",
        "ASOCIACION MUTUAL DE PROTECCION FAMILIAR", "GERDANNA S.A.", "O.S.V.V.R.A.", "ITER MEDICINA S.A.",
        "EN EL HOGAR", "PREVENCION SALUD S.A.", "CAMINOS PROTEGIDOS ART S.A.", "SEROS VALORES PAMI",
        "I.N.S.S.J.P.-VETER.DE GUERRA", "PROME S.A.", "LIDERAR S.A. ART", "PREVENCION ART",
        "SANCOR COOP.SEGUROS", "LA SEGUNDA ART", "INTERACCION ART", "FEDERACION PATRONAL SEGUROS S.A.",
        "EXPERTA ART S.A", "GALENO ART. S.A.", "BERKLEY ART", "I.N.S.S.J.P.",
        "O.S. SERVICIOS SOCIALES BANCARIOS (OSSSB)", "O.S.P.E.R.Y H.R.A",
        "OMINT ASEGURADORA DE RIESGO DEL TRABAJO S,A,", "CONFERENCIA EPISCOPAL ARGENTINA",
        "O.S.COND. CAMIONEROS (SANTA CRUZ)", "O.S.P.y G. CHUBUT", "I.O.S.F.A.", "O.S.P.E.D.Y.C.",
        "HEMISFERIO SALUD S.A.", "VISITAR SRL", "D.A.S.U.(U.N.P.S.J.B.)", "D.A.S.U.(I.V.A.)",
        "VALORES PAMI", "I.N.S.S.J.P. (SANTA CRUZ)", "SWISS MEDICAL S.A. (I.V.A.)", "A.M.F.F.A.",
        "A.P.S.O.T.", "F.S.S.T.", "O.S.D.E.", "O.S.D.E. (I.V.A.) 2-210 / 2-310", "SCIS OSFENTOS",
        "SCIS S.A. OSPESCA", "O.S.D.E. (IVA) 2-410", "O.S.D.E. (IVA) 2-450", "O.S.D.E.(IVA) 2-510",
        "VISITAR - OSDEPYM", "O.S.J.e R.A.", "SAN FRANCISCO A.R.T.", "UTEPLIM SALUD",
        "OSFATUN", "GRUPO ROISA", "NATIVUS", "O.S.F.A.T.L.Y.F.", "O.S.T.R.A.C.",
        "OBRA SOCIAL DEL PERSONAL DE FARMACIA", "GLOBAL EMPRESARIA S.A."
    ]
    N_OS_ORD = sorted(list(set(NOMBRES_OS)), key=len, reverse=True)

    resultados = []
    liq, p_liq, f_liq, cta, prof = "N/A", "N/A", "N/A", "N/A", "N/A"

    for i, l in enumerate(lineas):
        if "LIQUIDACIÓN DE HONORARIOS" in l.upper():
            liq = l
            m = re.search(r'(\d+/\d+)\s*-\s*(\d{2}/\d{2}/\d{4})', l)
            if m: p_liq, f_liq = m.group(1), m.group(2)
        if l.startswith('C') and '-' in l:
            m_p = re.search(r'(C\d+)\s*-\s*([^-\n]+)', l)
            if m_p: cta, prof = m_p.group(1), m_p.group(2).strip()

        m_per = re.match(r'^(\d{1,2}/\d{4})$', l)
        if m_per:
            periodo_fila = m_per.group(1)

            os_nombre = ""
            for offset in range(1, 8):
                if i - offset >= 0:
                    contexto = " ".join(lineas[i-offset:i]).upper()
                    for nombre in N_OS_ORD:
                        if nombre.upper() in contexto:
                            os_nombre = nombre; break
                    if os_nombre: break

            if not os_nombre or os_nombre == "No identificada":
                continue

            nums = []
            for cursor in range(i + 1, min(i + 20, len(lineas))):
                if re.match(r'^\d{1,2}/\d{4}$', lineas[cursor]) or lineas[cursor].startswith('C'):
                    break

                txt_val = lineas[cursor]
                matches = re.findall(r'-?\d{1,3}(?:\.\d{3})*(?:,\d{1,2})?', txt_val)
                if not matches and txt_val == "0,00": matches = ["0,00"]

                for m_val in matches:
                    nums.append(limpiar_monto_v14(m_val))
                if len(nums) >= 4: break

            if nums:
                h = g = v = t = 0.0
                if len(nums) >= 4:
                    h, g, v, t = nums[0], nums[1], nums[2], nums[3]
                elif len(nums) == 3:
                    if "IVA" in os_nombre.upper() or "I.V.A." in os_nombre.upper():
                        h, v, t = nums[0], nums[1], nums[2]
                    else:
                        h, g, t = nums[0], nums[1], nums[2]
                elif len(nums) == 2:
                    h, t = nums[0], nums[1]
                else:
                    h = t = nums[0]

                if len(nums) > 1: t = nums[-1]

                resultados.append({
                    "Liq": liq, "PeriLiq": p_liq, "FechaLiq": f_liq, "Cuenta": cta,
                    "Apellido y Nombre": prof, "Obra Social": os_nombre,
                    "Fact Período": periodo_fila, "Honorarios": h, "Gastos": g,
                    "Iva": v, "Total": t
                })

    df = pd.DataFrame(resultados).drop_duplicates()
    df['Control Total'] = df['Honorarios'] + df['Gastos'] + df['Iva']
    return df

def extraer_adicionales_v91(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    resultados = []
    TITULOS_ADIC = ["CRÉDITOS PROVENIENTE DE HONORARIOS", "DÉBITOS PROVENIENTE DE HONORARIOS",
                    "CRÉDITOS ADICIONALES", "DÉBITOS ADICIONALES"]

    for i in range(len(doc)):
        pagina = doc[i]
        lineas = [l.strip() for l in pagina.get_text("text").split('\n') if l.strip()]

        cuenta, profesional, fecha_liq = "N/A", "N/A", "N/A"
        dentro_de_bloque = False
        titulo_actual = ""
        buffer_leyenda = []

        for l in lineas:
            l_up = l.upper()

            if "LIQUIDACIÓN DE HONORARIOS" in l_up:
                m_fec = re.search(r'(\d{2}/\d{2}/\d{4})', l)
                if m_fec: fecha_liq = m_fec.group(1)
                continue
            m_p = re.search(r'(C\d+)\s*-\s*([^-\d\n]+)', l)
            if m_p:
                cuenta, profesional = m_p.group(1), m_p.group(2).strip()
                continue

            es_titulo = False
            for t in TITULOS_ADIC:
                if t in l_up:
                    dentro_de_bloque, titulo_actual, buffer_leyenda, es_titulo = True, t, [], True
                    break
            if es_titulo: continue
            if "DEDUCCIONES" in l_up or "TOTAL A COBRAR" in l_up:
                dentro_de_bloque = False
                continue

            if dentro_de_bloque:
                m_imp = re.search(r'(-?\s*[\d\.]+\s*,\s*[\d]{2})$', l)

                if m_imp:
                    valor_str = m_imp.group(1)
                    texto_previo = l[:m_imp.start()].strip()
                    if texto_previo: buffer_leyenda.append(texto_previo)

                    leyenda_full = " ".join(buffer_leyenda).strip()

                    if "(Prov. de Hon.)" in leyenda_full:
                        partes = leyenda_full.split("(Prov. de Hon.)")
                        if partes[1].strip():
                            valor_str = partes[1].strip()
                            leyenda_full = partes[0].strip() + " (Prov. de Hon.)"

                    leyenda_full = re.sub(r'^(Gastos Iva|Importe Gastos Iva|Facturas Cobradas a Liquidar|importe)\s*', '', leyenda_full, flags=re.IGNORECASE).strip()

                    if leyenda_full and "TOTAL" not in leyenda_full.upper():
                        resultados.append({
                            "Fecha Liq": fecha_liq, "Cuenta": cuenta, "Profesional": profesional,
                            "Título (Concepto)": titulo_actual, "Leyenda": leyenda_full,
                            "Importe": limpiar_importe_v91(valor_str)
                        })
                    buffer_leyenda = []
                else:
                    if not any(x in l_up for x in ["CUIT:", "PÁGINA", "FECHA:"]):
                        buffer_leyenda.append(l)

    doc.close()
    return pd.DataFrame(resultados) if resultados else pd.DataFrame(columns=["Fecha Liq", "Cuenta", "Profesional", "Título (Concepto)", "Leyenda", "Importe"])

def extraer_deducciones_v85(pdf_bytes):
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    resultados = []

    for i in range(len(doc)):
        pagina = doc[i]
        text = pagina.get_text("text")
        lineas = [l.strip() for l in text.split('\n') if l.strip()]

        cuenta, profesional, fecha_liq = "N/A", "N/A", "N/A"
        en_deducciones = False
        buffer_desc = []

        for l in lineas:
            l_up = l.upper()

            if "LIQUIDACIÓN DE HONORARIOS" in l_up:
                m_f = re.search(r'(\d{2}/\d{2}/\d{4})', l)
                if m_f: fecha_liq = m_f.group(1)
                continue
            m_p = re.search(r'(C\d+)\s*-\s*([^-\d\n]+)', l)
            if m_p:
                cuenta, profesional = m_p.group(1), m_p.group(2).strip()
                continue

            if "DEDUCCIONES" in l_up:
                en_deducciones = True
                buffer_desc = []
                continue

            if "TOTAL A COBRAR" in l_up or "NETO A COBRAR" in l_up:
                en_deducciones = False
                continue

            if en_deducciones:
                m_imp = re.search(r'(-\s*[\d\.]+,[\d]{2})$', l)

                if m_imp:
                    texto_linea = l[:m_imp.start()].strip()
                    if texto_linea: buffer_desc.append(texto_linea)

                    desc_full = " ".join(buffer_desc).strip()

                    m_per = re.search(r'\(Periodo\s+(\d{1,2}/\d{4})\)', desc_full, re.IGNORECASE)
                    periodo = m_per.group(1) if m_per else ""

                    desc_final = re.sub(r'\(Periodo\s+\d{1,2}/\d{4}\)', '', desc_full).strip()
                    desc_final = desc_final.replace("importe", "").strip()

                    if desc_final and "TOTAL" not in desc_final.upper():
                        resultados.append({
                            "Fecha Liq": fecha_liq,
                            "Cuenta": cuenta,
                            "Profesional": profesional,
                            "Deducción": desc_final,
                            "Periodo": periodo,
                            "Importe": limpiar_num_deduc(m_imp.group(1))
                        })
                    buffer_desc = []
                else:
                    if not any(x in l_up for x in ["CUIT:", "PÁGINA", "FECHA:", "IMPORTE"]):
                        buffer_desc.append(l)

    doc.close()
    return pd.DataFrame(resultados) if resultados else pd.DataFrame(columns=["Fecha Liq", "Cuenta", "Profesional", "Deducción", "Periodo", "Importe"])

# --- Consolidation Function ---

def consolidate_and_export(df_final_v14, df_adicionales_v91, df_deducciones):
    # Preparar DataFrame de Honorarios para el totalizador
    df_honorarios_totalizador = df_final_v14.copy()
    df_honorarios_totalizador['FechaLiq'] = pd.to_datetime(df_honorarios_totalizador['FechaLiq'], format='%d/%m/%Y', errors='coerce')
    df_honorarios_totalizador = df_honorarios_totalizador.rename(columns={'FechaLiq': 'Fecha_Liq', 'Apellido y Nombre': 'Profesional'})
    df_honorarios_totalizador['Profesional'] = df_honorarios_totalizador['Profesional'].str.strip().str.upper()
    df_honorarios_totalizador['Cuenta'] = df_honorarios_totalizador['Cuenta'].str.strip().str.upper()
    df_honorarios_totalizador = df_honorarios_totalizador.dropna(subset=['Fecha_Liq']) # Eliminar filas con fechas inválidas
    df_honorarios_grouped = df_honorarios_totalizador.groupby(['Profesional', 'Cuenta', 'Fecha_Liq'])['Control Total'].sum().reset_index()
    df_honorarios_grouped = df_honorarios_grouped.rename(columns={'Control Total': 'Total Honorarios'})

    # Preparar DataFrame de Adicionales para el totalizador
    df_adicionales_totalizador = df_adicionales_v91.copy()
    df_adicionales_totalizador['Fecha Liq'] = pd.to_datetime(df_adicionales_totalizador['Fecha Liq'], format='%d/%m/%Y', errors='coerce')
    df_adicionales_totalizador = df_adicionales_totalizador.rename(columns={'Fecha Liq': 'Fecha_Liq'})
    df_adicionales_totalizador['Profesional'] = df_adicionales_totalizador['Profesional'].str.strip().str.upper()
    df_adicionales_totalizador['Cuenta'] = df_adicionales_totalizador['Cuenta'].str.strip().str.upper()
    df_adicionales_totalizador = df_adicionales_totalizador.dropna(subset=['Fecha_Liq']) # Eliminar filas con fechas inválidas
    df_adicionales_grouped = df_adicionales_totalizador.groupby(['Profesional', 'Cuenta', 'Fecha_Liq'])['Importe'].sum().reset_index()
    df_adicionales_grouped = df_adicionales_grouped.rename(columns={'Importe': 'Total Adicionales'})

    # Preparar DataFrame de Deducciones para el totalizador
    df_deducciones_totalizador = df_deducciones.copy()
    df_deducciones_totalizador['Fecha Liq'] = pd.to_datetime(df_deducciones_totalizador['Fecha Liq'], format='%d/%m/%Y', errors='coerce')
    df_deducciones_totalizador = df_deducciones_totalizador.rename(columns={'Fecha Liq': 'Fecha_Liq'})
    df_deducciones_totalizador['Profesional'] = df_deducciones_totalizador['Profesional'].str.strip().str.upper()
    df_deducciones_totalizador['Cuenta'] = df_deducciones_totalizador['Cuenta'].str.strip().str.upper()
    df_deducciones_totalizador = df_deducciones_totalizador.dropna(subset=['Fecha_Liq']) # Eliminar filas con fechas inválidas
    df_deducciones_grouped = df_deducciones_totalizador.groupby(['Profesional', 'Cuenta', 'Fecha_Liq'])['Importe'].sum().reset_index()
    df_deducciones_grouped = df_deducciones_grouped.rename(columns={'Importe': 'Total Deducciones'})

    # Consolidar para la hoja 'Totalizador'
    df_totalizador = pd.merge(
        df_honorarios_grouped,
        df_adicionales_grouped,
        on=['Profesional', 'Cuenta', 'Fecha_Liq'],
        how='outer'
    )
    df_totalizador = pd.merge(
        df_totalizador,
        df_deducciones_grouped,
        on=['Profesional', 'Cuenta', 'Fecha_Liq'],
        how='outer'
    )

    df_totalizador = df_totalizador.fillna(0)
    df_totalizador['Total a Cobrar'] = df_totalizador['Total Honorarios'] + df_totalizador['Total Adicionales'] + df_totalizador['Total Deducciones']
    df_totalizador = df_totalizador.sort_values(by=['Fecha_Liq', 'Profesional', 'Cuenta']).reset_index(drop=True)
    df_totalizador['Fecha_Liq'] = df_totalizador['Fecha_Liq'].dt.strftime('%d/%m/%Y')

    # Generar el archivo Excel único en memoria
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df_final_v14.to_excel(writer, sheet_name='Honorarios', index=False)
        df_adicionales_v91.to_excel(writer, sheet_name='Adicionales', index=False)
        df_deducciones.to_excel(writer, sheet_name='Deducciones', index=False)
        df_totalizador.to_excel(writer, sheet_name='Totalizador', index=False)
    output.seek(0)
    return output

# --- Streamlit App ---

st.set_page_config(page_title="Procesador de Recibos PDF", layout="wide")
st.title("📄 Procesador Automático de Recibos de Liquidación")
st.markdown("Sube tu archivo PDF y obtén un Excel consolidado con Honorarios, Adicionales, Deducciones y un Totalizador.")

uploaded_file = st.file_uploader("Selecciona un archivo PDF", type="pdf")

if uploaded_file is not None:
    st.success("PDF cargado exitosamente.")
    pdf_bytes = uploaded_file.read()

    if st.button("✨ Procesar Recibos"):
        with st.spinner("Extrayendo datos y generando Excel... esto puede tardar unos minutos."):
            try:
                # Extract data
                df_honorarios = extraer_honorarios_v14(pdf_bytes)
                df_adicionales = extraer_adicionales_v91(pdf_bytes)
                df_deducciones = extraer_deducciones_v85(pdf_bytes)

                # Consolidate and get Excel bytes
                excel_output = consolidate_and_export(df_honorarios, df_adicionales, df_deducciones)

                st.download_button(
                    label="Descargar Excel Consolidado",
                    data=excel_output,
                    file_name=f"Liquidaciones_consolidadas_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
                st.balloons()
                st.success("¡Procesamiento completado y Excel listo para descargar!")

            except Exception as e:
                st.error(f"Ocurrió un error durante el procesamiento: {e}")
                st.exception(e)

else:
    st.info("Por favor, sube un archivo PDF para comenzar.")
