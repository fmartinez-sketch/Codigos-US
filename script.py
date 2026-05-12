import googlemaps
import pandas as pd
import time
import os

#  CONFIGURACIÓN 
API_KEY = os.getenv('MAPS_API_KEY') 
gmaps = googlemaps.Client(key=API_KEY)

def buscar_salones(zip_code):
    all_results = []
    query = f"beauty salon in zip code {zip_code}, USA"
    try:
        response = gmaps.places(query=query)
        while True:
            results = response.get('results', [])
            for place in results:
                place_id = place.get('place_id')
                # Obtenemos detalles específicos de cada lugar
                details = gmaps.place(place_id=place_id, fields=['name', 'formatted_phone_number', 'website', 'formatted_address', 'rating', 'user_ratings_total']).get('result', {})
                all_results.append({
                    'Nombre': details.get('name'),
                    'Teléfono': details.get('formatted_phone_number'),
                    'Sitio Web': details.get('website'),
                    'Dirección': details.get('formatted_address'),
                    'Rating': details.get('rating'),
                    'Total Reseñas': details.get('user_ratings_total'),
                    'ZIP Code': zip_code
                })
            
            next_page_token = response.get('next_page_token')
            if not next_page_token: 
                break
            
            time.sleep(2) # Pausa obligatoria para que el token de la siguiente página sea válido
            response = gmaps.places(query=query, page_token=next_page_token)
    except Exception as e:
        print(f"Error procesando ZIP {zip_code}: {e}")
    return all_results

# PROCESAMIENTO POR LOTES
archivo_zip = "codigos_postales_US.csv"
archivo_progreso = "progreso.txt"
archivo_salida = "reporte_acumulado.csv"
LIMITE_DIARIO = 100 # Cantidad de ZIP Codes por dia

if os.path.exists(archivo_zip):
    df_zips = pd.read_csv(archivo_zip, dtype=str)
    # Limpieza de datos: asegurar 5 dígitos y eliminar duplicados
    zip_list = df_zips.iloc[:, 0].str.zfill(5).unique().tolist()
    total_zips = len(zip_list)

    # 1. Leer el índice de inicio desde el archivo de progreso
    indice_inicio = 0
    if os.path.exists(archivo_progreso):
        with open(archivo_progreso, "r") as f:
            try:
                indice_inicio = int(f.read().strip())
            except ValueError:
                indice_inicio = 0

    # 2. Si el índice ya superó el total, reiniciar a 0
    if indice_inicio >= total_zips:
        print("¡Fin de lista alcanzado! Reiniciando desde el principio.")
        indice_inicio = 0

    # 3. Determinar el rango de hoy (máximo 100 o lo que falte para el final)
    indice_fin = min(indice_inicio + LIMITE_DIARIO, total_zips)
    zips_a_procesar = zip_list[indice_inicio:indice_fin]

    print(f"--- Iniciando sesión: Procesando del índice {indice_inicio} al {indice_fin-1} ---")

    resultados_totales_hoy = []
    
    for i, zip_hoy in enumerate(zips_a_procesar):
        print(f"[{i+1}/{len(zips_a_procesar)}] Buscando en ZIP: {zip_hoy}...")
        data = buscar_salones(zip_hoy)
        if data:
            resultados_totales_hoy.extend(data)
        
        # Pequeña pausa entre códigos postales para no saturar la cuota por segundo
        time.sleep(0.5)

    # 4. Guardar resultados si hubo hallazgos
    if resultados_totales_hoy:
        df_hoy = pd.DataFrame(resultados_totales_hoy)
        header = not os.path.exists(archivo_salida)
        df_hoy.to_csv(archivo_salida, mode='a', index=False, header=header, encoding='utf-8-sig')
        print(f"Éxito: Se guardaron {len(resultados_totales_hoy)} registros.")

    # 5. Actualizar el progreso para la ejecución de mañana
    nuevo_indice = indice_fin
    # Si terminamos justo en el último, el siguiente será 0
    if nuevo_indice >= total_zips:
        nuevo_indice = 0
        
    with open(archivo_progreso, "w") as f:
        f.write(str(nuevo_indice))
    
    print(f"Progreso actualizado. Próximo inicio en índice: {nuevo_indice}")
else:
    print(f"Error: No se encontró el archivo {archivo_zip}")
