import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pyproj


import dash
import dash_bootstrap_components as dbc
from dash import Dash, dcc, html, Input, Output, callback, State, dash_table
import psycopg2
from psycopg2.extensions import AsIs
import math
import numpy as np
from flask import send_from_directory
import pandas as pd
import os


external_stylesheets = [
    {
        'href': 'static/styles.css',
        'rel': 'stylesheet'
    }
]

app = Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP, {
        'href': '../static/styles.css',
        'rel': 'stylesheet'
}, dbc.icons.BOOTSTRAP], title='Tuneleras')
server = app.server

csv_data_tramos = pd.read_csv('Datos.csv', delimiter = ',')


def rotate_xMatriz(angle):
        """" Devuelve la matriz de rotacion que rota `angle` en el eje `x` """
        c = math.cos(angle)
        s = math.sin(angle)
        return [[1, 0, 0],
                [0, c, -s],
                [0, s, c]]

def rotate_yMatriz(angle):
    """" Devuelve la matriz de rotacion que rota `angle` en el eje `y` """
    c = math.cos(angle)
    s = math.sin(angle)
    return [[c, 0, s],
            [0, 1, 0],
            [-s, 0, c]]

def rotate_zMatriz(angle):
    """" Devuelve la matriz de rotacion que rota `angle` en el eje `z` """
    c = math.cos(angle)
    s = math.sin(angle)
    return [[c, -s, 0],
            [s, c, 0],
            [0, 0, 1]]

def crear_plano(puntos_array, datos):
    """" Devuelve un plano que pasa por tres puntos 
            PARAMETROS: `puntos_array` array de tres puntos por los que debe pasar el plano
    """
    v1Plano = np.array(puntos_array[1]) - np.array(puntos_array[0])
    v2Plano = np.array(puntos_array[2]) - np.array(puntos_array[0])
    #normal = np.cross(v1, v2)
    normalPlano = [v1Plano[1] * v2Plano[2] - v1Plano[2] * v2Plano[1],
                    v1Plano[2] * v2Plano[0] - v1Plano[0] * v2Plano[2],
                    v1Plano[0] * v2Plano[1] - v1Plano[1] * v2Plano[0]
                    ]
    a, b, c = normalPlano
    d = np.dot(normalPlano, puntos_array[0])
    #print(f"{a}x {b}y {c}z {d} = 0")

    # Genera una malla de puntos en el plano
    X, Y = np.meshgrid(np.linspace(0, datos[0][6], 10), np.linspace(-3, 3, 10))
    Z = (d - a*X - b*Y) / c
    return X, Y, Z

def crear_cilindro_mesh3d(Xcoord_C1, Ycoord_C1, ZCoord_C1, Xcoord_C2, Ycoord_C2, Zcoord_C2, radio_C1, radio_C2, color, opacity, info, eje, angle, name, trunco:bool, cota_inicial, cota_final, n):
        """
            Funcion que crea un cilindro a aprtir de dos circunferencias
            Parametros: `Xcoord_C1:` coordenada en X del centro de la circunferencia 1
                        `Xcoord_C2:` coordenada en X del centro de la circunferencia 1
                        `Ycoord_C1:` coordenada en Y del centro de la circunferencia 1
                        `Ycoord_C2:` coordenada en Y del centro de la circunferencia 1
                        `Zcoord_C1:` coordenada en Z del centro de la circunferencia 1
                        `Zcoord_C2:` coordenada en Z del centro de la circunferencia 1
                        `radio_C1:` radio de la circunferencia 1
                        `radio_C2:` radio de la circunferencia 2
                        `color:` color del cilindro
                        `opacity:` opacidad del cilindro
                        `info:` informacion que se verá si paso el mouse por el cilidnro en la grafica
                        `eje:` eje de rotacion 
                        `angle:` angulo en radianes para rotar
                        `name:` nombre del cilidro
                        `trunco:` bool-> si es verdadero truncara las coordenasdas en z de los vertices que esten por encima de la cota de terreno(les resta la distancia para que se siga dibujando bien)
                        
            IMPORTANTE:  Observar que la diferencia entre las coordenadas en Z de ambas circunferencias determina el largo del cilindro 
                         Al rotar el cilindro en algun eje tambien rotan sus ejes locales, por lo que algunas coordenas cambian (ejemplo, al rotarse en ele eje y, las coordenas x, z se intercambain)
            
            Return: La funcion regresa una lista con tres objetos
                    [0] Objeto Mesh3d 
                    [1] Array con las coordenadas de la circunferencia 1
                    [2] array con las coordenadas de la circunferencia 2
                        
        """
        x_c1 = [Xcoord_C1 + radio_C1*np.cos(t) for t in np.linspace(0, 2*np.pi, n)]
        y_c1 = [Ycoord_C1 + radio_C1*np.sin(t) for t in np.linspace(0, 2*np.pi, n)]
        z_c1 = [ZCoord_C1 for t in np.linspace(0, 2*np.pi, n)]

        x_c2 = [Xcoord_C2 + radio_C2*np.cos(t) for t in np.linspace(0, 2*np.pi, n)]
        y_c2 = [Ycoord_C2 + radio_C2*np.sin(t) for t in np.linspace(0, 2*np.pi, n)]
        z_c2 = [Zcoord_C2 for t in np.linspace(0, 2*np.pi, n)]
        

                
        #Roto las circunferencias 
        if(eje == 'y'):
            rotation_matrix = rotate_yMatriz(angle)
        else:
            rotation_matrix = rotate_xMatriz(angle)
            
        matrizC1 = list(zip(x_c1, y_c1, z_c1))
        matrizC1 = [list(t) for t in matrizC1]

        matrizC2 = list(zip(x_c2, y_c2, z_c2))
        matrizC2 = [list(t) for t in matrizC2]
        x_rc1 = []
        y_rc1 = []
        z_rc1 = []

        for row in matrizC1:
            rotated = np.dot(row, rotation_matrix)
            x_rc1.append(rotated[0])
            y_rc1.append(rotated[1])
            z_rc1.append(rotated[2])

        x_rc2 = []
        y_rc2 = []
        z_rc2 = []

        for row in matrizC2:
            rotated = np.dot(row, rotation_matrix)
            x_rc2.append(rotated[0])
            y_rc2.append(rotated[1])
            z_rc2.append(rotated[2])
            
            
        ####################################################################################
        # TRUNCO RED ZONE A COTA DE TERRENO, PARA QUE LA ZONA ROJA NO SOBREPASE EL TERRENO #
        ####################################################################################
        if(trunco):
            for i in range(0, len(z_rc1)):
                if(z_rc1[i] > cota_inicial[0][0]):
                    z_rc1[i] = z_rc1[i] - (z_rc1[i] - cota_inicial[0][0])

            
            for i in range(0, len(z_rc2)):
                if(z_rc2[i] > cota_final[0][0]):
                    z_rc2[i] = z_rc2[i] - (z_rc2[i] - cota_final[0][0])

        # Coordenadas de los vértices
        xcy1 = []
        ycy1 = []
        zcy1 = []

        for k in range(0, n, 1):
            xcy1 = xcy1 + [x_rc1[k], x_rc2[k]]
            ycy1 = ycy1 + [y_rc1[k], y_rc2[k]]
            zcy1 = zcy1 + [z_rc1[k], z_rc2[k]]

        ViCy1 = []
        VjCy1 = []
        VkCy1 = []

        for i in range((n*2) - 2):
            ViCy1.append(i % ((n*2) - 1))
            VjCy1.append((i+1) % ((n*2) - 2))
            VkCy1.append(((i+1) % ((n*2) - 2)) + 1)
            
        # Crear una malla de la caras laterales del cilindro
        return [go.Mesh3d(x = xcy1,
                          y = ycy1,
                          z = zcy1,
                          i = ViCy1,
                          j = VjCy1,
                          k = VkCy1, 
                          color = color,
                          opacity = opacity, 
                          flatshading = True,
                          intensitymode = 'cell',
                          lightposition = dict(x = 0, y = 0, z = 0),
                          lighting = dict(ambient = .8, facenormalsepsilon = 1e-12, vertexnormalsepsilon = 1e-12, roughness = 1, diffuse = 1, specular = .2, fresnel = 0),
                          hovertemplate=info,
                          name = name),
                [x_rc1, y_rc1, z_rc1],
                [x_rc2, y_rc2, z_rc2]]


def make_map_2(tramos_csv, id, dis_esq, ang_tun):
    datos_CSV = tramos_csv.iloc[int(id)][0:16]
    datos = [datos_CSV]
    x = float(datos[0][12])
    y = float(datos[0][13])
    transformer = pyproj.Transformer.from_crs("EPSG:32721", "EPSG:4326")


    coords_puntos = csv_data_tramos.iloc[int(id)][16]
    array_puntos = str(coords_puntos).split(",")
    array_maps = []
    center_lat = 0
    center_lon = 0
    len_array_puntos = len(array_puntos)
    lat_array = []
    lon_array = []
    hover_data = []
    
    for i in range(0, len_array_puntos):
        array_aux = array_puntos[i].split(" ")
        x = float(array_aux[1])
        y = float(array_aux[2])
        
        lat, lon = transformer.transform(x, y)
        lat_array.append(str(lat))
        lon_array.append(str(lon))
        

        center_lat += lat
        center_lon += lon
        hover_data.append(str(x) + " " + str(y) + "  " + str(i))
    
    text_data = ['AA']
    if(datos[0][6] == 'IMP'):
        text_data = ['aa']
        
    for i in range(0, len(lat_array)-2):
        text_data.append(" ")
    
    if(datos[0][6] != 'IMP'):
        text_data.append('aa')
    else:
        text_data.append('AA')
    
    
   
    map_tramo = go.Scattermapbox(
        lat=lat_array,
        lon=lon_array,
        mode = 'lines+markers+text',
        marker = go.scattermapbox.Marker(
            size = 5,
            color = 'rgba(200, 30, 100, 1)',
            
        ),
        text = text_data,
        textposition = 'bottom center',
        hoverinfo = 'text',
        hovertext = hover_data,
        name = "Tramo"
    )
    
    array_maps.append(map_tramo)
    aux = seleccionar_sub_tramo_list(dis_esq, array_puntos)
    
    aux1 = aux[0].split(' ')
    aux2 = aux[1].split(' ')
    dist_Aux = aux[2]
    indices = aux[3]
    x2 = float(aux1[1])
    y2 = float(aux1[2])
    x1 = float(aux2[1])
    y1 = float(aux2[2])
    pendiente = (y2 - y1) / (x2 - x1) 
    def recta_tramo(X) -> float:  
        """ recta que une los dos puntos del tramo"""
        return pendiente * X - (pendiente*x1) + y1
    

    #(x1, y1) aa
    #(x2, y2) AA
    AA_in_der_aux = -1
    if(x1 >= x2):
        AA_in_der_aux = 1

    #angulo de la pendient del tramo
    angle = (math.atan(pendiente)) 
    hipotenusa_dis = abs(float(dist_Aux-dis_esq)) 
    dis_cateto_adj = AA_in_der_aux * round(math.cos(angle) * hipotenusa_dis, 2)  #si AA esta a la derecha de aa sino *-1
    a = math.pow(x2 - (x2+dis_cateto_adj), 2)
    b = math.pow(recta_tramo(x2) - recta_tramo(x2+dis_cateto_adj), 2)
        
    def recta_tun(X) -> float:  
        """ recta que une los dos puntos de la tunelera"""
        x_1 = x2 + dis_cateto_adj
        y_1 = recta_tramo(x2 + dis_cateto_adj)
        m = (-1/(pendiente))
        m_ajustada = math.tan(math.atan(m) + math.radians(-float(ang_tun)))
        m = m_ajustada
        return  m * X - (m*x_1) + y_1
    

    m1 = pendiente
    m2 = (-1/(pendiente))
    m_ajustada = math.tan(math.atan(m2) + math.radians(-float(ang_tun)))
    m2 = m_ajustada
    angulo_rectas = 0
    if(m2*m1 != -1):
        angulo_rectas = math.atan((m2 - m1) / (1 + (m2 * m1)))
    else:
        angulo_rectas = math.pi/2
        
    
    lat_pt_tramo1, lon_pt_tramo1 = transformer.transform(x2 + dis_cateto_adj, recta_tramo(x2 + dis_cateto_adj))
    lat_pt_tramo2, lon_pt_tramo2 = transformer.transform(x2 + dis_cateto_adj - 4, recta_tun(x2 + dis_cateto_adj - 4))
    lat_pt_tramo3, lon_pt_tramo3 = transformer.transform(x2 + dis_cateto_adj + 4, recta_tun(x2 + dis_cateto_adj + 4))
    
    lat_pt_angle, lon_pt_angle = transformer.transform(x2 + dis_cateto_adj + 3, recta_tramo(x2 + dis_cateto_adj))
    
    map_angle = go.Scattermapbox(
        lat = [lat_pt_angle],
        lon = [lon_pt_angle],
        mode = 'text',
        text = 'ángulo: ' + str(math.degrees(angulo_rectas))
    )
    
    map_tunelera = go.Scattermapbox(
        lat = [lat_pt_tramo1, lat_pt_tramo2, lat_pt_tramo3],
        lon = [lon_pt_tramo1, lon_pt_tramo2, lon_pt_tramo3],
        mode = 'lines+text',
        marker = go.scattermapbox.Marker(
            size = 4,
            color = 'rgba(10, 70, 80, 1)',
            
        ),
        text = ['', '', 'Tunelera'],
        name = "Tunelera"
                        
    )
    lat_array_dis = []
    lon_array_dis = []
    for i in range(0, indices[1]):
        lat_array_dis.append(lat_array[i])
        lon_array_dis.append(lon_array[i])
        
    if(len(lat_array_dis) == 0):
        lat_array_dis.append(lat_array[0])
        lon_array_dis.append(lon_array[0])
        
    lat_array_dis.append(lat_pt_tramo1)
    lon_array_dis.append(lon_pt_tramo1)

    map_dis = go.Scattermapbox(
        lat = lat_array_dis,
        lon = lon_array_dis,
        mode = 'lines+text',
        marker = go.scattermapbox.Marker(
            size = 3,
            color = 'rgba(20,20,20,1)'
            
        ),
        #text = ['', 'dis: ' + str(round(math.sqrt(a + b), 1)) + 'm', '']
        text = ['', 'dis: '+ str(dis_esq) + 'm', ''],
        showlegend = False
    )
    
    
    
    
    # array_maps.append(map_tunelera)
    # array_maps.append(map_dis)
    array_maps.extend([map_angle, map_tunelera, map_dis])
    fig = go.Figure(data = array_maps)
    fig.update_layout(
        mapbox = dict(
            accesstoken=os.getenv('MAPBOX_API_KEY'),
            style = 'light', 
            center = go.layout.mapbox.Center(
                lat = center_lat/len_array_puntos,
                lon = center_lon/len_array_puntos
            ),
            zoom = 18
        ),
        margin = {"r":0,"t":1,"l":0,"b":0}
    )
    return fig
 
def calcular_distancia_al_origen(punto):
    #distancia = math.sqrt(**2 + float(punto[2])**2)
    distancia = math.atan2(float(punto[2]), float(punto[1]))
    return distancia

def ordenar_puntos_por_distancia_al_origen(puntos):
    puntos_ordenados = sorted(puntos, key=calcular_distancia_al_origen)
    return puntos_ordenados

def distancia_punto_a_recta(A, B, C, P):
    #formula de distancioa de punto a recta
    return abs(A*P[0]+B*P[1]+C)/(math.sqrt(A*A+B*B))

def distancia_entre_puntos(A, B):
    acum = 0
    for i in range(0, len(A)):
        acum += math.pow((B[i] - A[i]), 2)
        
    return math.sqrt(acum)

def seleccionar_sub_tramo_list(x_dis, array_puntos)->list:
    """_summary_

    Args:
        x_dis (_type_): _description_
        array_puntos (_type_): _description_

    Returns:
        list: _description_
    """
    
    
    dis = distancia_entre_puntos([0, 0], [0, 0])
    i = 0
    len_array = len(array_puntos)
    while(i < (len(array_puntos)-2)):
        x1 = float(array_puntos[i].split(' ')[1])
        y1 = float(array_puntos[i].split(' ')[2])
        x2 = float(array_puntos[i+1].split(' ')[1])
        y2 = float(array_puntos[i+1].split(' ')[2])
        P1 = [x1, y1]
        P2 = [x2, y2]
        dis += distancia_entre_puntos(P1, P2)
        if(dis >= float(x_dis)):
            return [array_puntos[i+1], array_puntos[i], dis, [i+1, i]]
        else:
            i+=1
    return [array_puntos[len_array-2], array_puntos[len_array-1], dis, [len_array-2, len_array-1]]
    
def seleccionar_sub_tramo(x_dis, array_dis)->int:
    """Devuelve el primer indice en el arreglo que sepuera o es igual a x_dis 

    Args:
        x_dis (float): distancia de tunelera a aguas arriba
        array_puntos array de distancias en eje x contando desde el primer punto a cada uno de los puntos del tramo
    """
    
    i = len(array_dis)-2
    while(i > 0 ):
        if(x_dis >= array_dis[i]):
            return i
        else:
            i -= 1
    return i
    
def create_graph(id_tramo, diametro_tunelera, profundidad_tunelera, dis_esquina, ang_tun):
    app.server.my_variable = 'Initial value'
    app.server.danger_type = ''
    app.server.many_points = True

    
    id_tramo = abs(int(id_tramo))
    if int(id_tramo) == 0:
        print("id = 0")
        app.server.my_variable = 'Danger!!'

    datos_CSV = csv_data_tramos.iloc[int(id_tramo)][1:8]
    datos = [datos_CSV]
    
    cota_inicial_CSV = csv_data_tramos.iloc[int(id_tramo)][8:10]
    cota_final_CSV = csv_data_tramos.iloc[int(id_tramo)][10:12]
    cota_inicial = [cota_inicial_CSV]
    cota_final = [cota_final_CSV]
    coords_puntos_tapas = csv_data_tramos.iloc[int(id_tramo)][12:16]
    
    coords_puntos = csv_data_tramos.iloc[int(id_tramo)][16]
    array_puntos = str(coords_puntos).split(",")
    if(len(array_puntos) > 20):
        app.server.many_points = False
    # HAGO UNA RECTA QUE UNE EL PRIMER CON EL ULTIMO PUNTO (estos estaran en y = 0)
    primer_punto_tramo = array_puntos[0]
    ultimo_punto_tramo = array_puntos[len(array_puntos)-1]
    
    y1 = float(primer_punto_tramo.split(' ')[2])
    x1 = float(primer_punto_tramo.split(' ')[1])
    
    y2 = float(ultimo_punto_tramo.split(' ')[2])
    x2 = float(ultimo_punto_tramo.split(' ')[1])
    pendiente_tramo_en_plano_XY = (y2 - y1) / (x2 - x1) 
    #A B C son los valores de la recta escrita de forma implicita Ax +By +C = 0, despejo de forma parametrica m(x - x1) = y - y1 (m es la pendiente de la recta)
    A = pendiente_tramo_en_plano_XY
    B = -1
    C = y1 - pendiente_tramo_en_plano_XY * x1
    distancias_de_puntos_a_recta_ejeY = []
    distancias_de_punto_inicial_a_intermedios = []
    distancias_de_puntos_a_recta_ejeX = []

    for i in range(0, len(array_puntos)):
        
        punto_intermedio = array_puntos[i]
        y3 = float(punto_intermedio.split(' ')[2])
        x3 = float(punto_intermedio.split(' ')[1])
        

        P = [x3, y3]
        distancia_punto_de_tramo_a_rectaY = distancia_punto_a_recta(A, B, C, P)
        #print("distancia de : " + str(i) + " "  + str(distancia_punto_de_tramo_a_recta))
        distancias_de_puntos_a_recta_ejeY.append(distancia_punto_de_tramo_a_rectaY)
        
        P1 = [x1, y1]
        distancia_punto_inicial_e_intermedio = distancia_entre_puntos(P1, P)
        distancias_de_punto_inicial_a_intermedios.append(distancia_punto_inicial_e_intermedio)
        #Uso pitagoras para hallar coord en x local
        distancia_en_eje_x = math.sqrt(math.pow(distancia_punto_inicial_e_intermedio, 2) + math.pow(distancia_punto_de_tramo_a_rectaY, 2))
        distancias_de_puntos_a_recta_ejeX.append(distancia_en_eje_x)
        
    # for i in range(0, len(array_puntos)):
    #     print(array_puntos[i])

    if cota_inicial[0][0] == 0 and cota_final[0][0] == 0:
        fig = go.Figure(data=[])
        app.server.my_variable = 'Danger!!'
        app.server.danger_type = 'Danger01'

    elif (cota_inicial[0][0] == 0):
        fig = go.Figure(data=[])
        app.server.my_variable = 'Danger!!'
        app.server.danger_type = 'Danger02'

    elif cota_final[0][0] == 0:
        fig = go.Figure(data=[])
        app.server.my_variable = 'Danger!!'



    diam = max(float(datos[0][2]), float(datos[0][3]))
    zabajo = float(datos[0][5])
    zarriba = float(datos[0][4])

    color_colector_Hex = '#808080'
    color_colector_Rgba = 'rgba(128, 128, 128, .5)'
    color_colector_Rgba = 'rgba(181, 181, 181, 1)'
    #factor es un dato consensuado, se lo pregunte a Nati, es el valor margen para construir alrededor de una tunelera
    if (datos[0][1] == 'ART'):
        espesor_arriba = 0.4
        espesor_abajo = 0.5
        factor = 4
        color_colector_Rgba = 'rgba(157, 67, 44, 1)' #Color ladrillo para los tipo arteaga
    else:
        if (float(datos[0][3]) > 0.7):
            espesor_arriba = 0.2
        else:
            espesor_arriba = 0.1
        factor = 2
        espesor_abajo = 0.3




    res = (x2-x1)**2 + (y2-y1)**2

    if (res > 0):
        xf = math.sqrt(res)
    else:
        app.server.my_variable = 'Danger!!'
        app.server.danger_type = 'Danger01'
        xf = .5

    

    # Coordenadas del centro de la circunferencia
    x1 = ((zarriba + diam + espesor_arriba) + (zarriba - espesor_abajo)) / 2 #Las coordenadas en x pasan a ser la altura al rotar los objectos, ya que rotan en local y sus ejes tambien rotan
    y1 = 0
    z1 = 0 #Las coordenadas en z pasan a ser el eje x

    x2 = ((zabajo + diam + espesor_arriba) + (zabajo - espesor_abajo)) / 2
    y2 = 0
    z2 = -xf

    r1 = (zarriba + diam + espesor_arriba) - x1
    r2 = (zabajo + diam + espesor_arriba) - x2

    y_redzone_1 = x1 - r1 - (factor*diametro_tunelera) #zarriba - factor*diametro_tunelera - espesor_abajo
    y_redzone_2 = x2 - r2 - (factor*diametro_tunelera)#zabajo - factor*diametro_tunelera - espesor_abajo

    y_redzone_12 = x1 + r1 + (factor*diametro_tunelera)#diametro_tunelera + zarriba + factor*diametro_tunelera + espesor_arriba
    y_redzone_22 = x2 + r2 + (factor*diametro_tunelera)#diametro_tunelera + zabajo + factor*diametro_tunelera + espesor_arriba
    
    x3 = (y_redzone_1 + y_redzone_12) / 2
    y3 = 0
    z3 = 0

    x4 = (y_redzone_2 + y_redzone_22) / 2
    y4 = 0
    z4 = -xf

    n = 31
    # Radios de las circunferencia

    r3 = y_redzone_1 - x3
    r4 = y_redzone_2 - x4

    def recta_zampeado(X) -> float:
        """recta que interpola los zampeados zarriba y zabajo

        Args:
            X (float): valor de X a evaluar en la recta

        Returns:
            float: devuelve el valor interpolado del zampeado en X
        """
 
        y2 = zarriba
        y1 = zabajo
        x2 = datos[0][6]
        x1 = 0
        pendiente = (y2 - y1) / (x2 - x1) 
        return pendiente * X - (pendiente*x1) + y1
    ###################################    ######################################################################################################
    # FUNCION PARA CREAR CILINDROS 3D #    #RETORNA UNA MESH3D DEL CILINDRO Y DOS MATRICES CON LAS COORDS DE LAS CIRCUNFERENECIAS QUE LO FORMAN #
    ###################################    ######################################################################################################
    array_tramos_cilindro_mesh = []
    array_tramos_cilindro_mesh2 = []
    array_tramos_cilindors_redZone_mesh = []
    distancias_de_puntos_a_recta_ejeZ = np.linspace(x1, x2, len(distancias_de_puntos_a_recta_ejeX))
    
    
    
    for i in range(0, len(distancias_de_puntos_a_recta_ejeX)-1):
        caras_lados_cilindro_colector2 = crear_cilindro_mesh3d(distancias_de_puntos_a_recta_ejeZ[i], distancias_de_puntos_a_recta_ejeY[i], -distancias_de_puntos_a_recta_ejeX[i], 
                                                               distancias_de_puntos_a_recta_ejeZ[i+1], distancias_de_puntos_a_recta_ejeY[i+1], -distancias_de_puntos_a_recta_ejeX[i+1], r1, r2, 
                                                            color_colector_Rgba, 1, 'Colector' + str(i), 'y', 
                                                            math.pi / 2, name = 'ladoTramo' + str(i), trunco = False, 
                                                            cota_final = cota_final, cota_inicial = cota_inicial, n = n)
        array_tramos_cilindro_mesh.append(caras_lados_cilindro_colector2[0])
        
        #Para ahorrar memoria y recursos al dibujar solo la parte interior en los extremos
        if(i == 0 or i == len(distancias_de_puntos_a_recta_ejeX)-1):
            caras_lados_cilindro_colector3 = crear_cilindro_mesh3d(distancias_de_puntos_a_recta_ejeZ[i], distancias_de_puntos_a_recta_ejeY[i], -distancias_de_puntos_a_recta_ejeX[i], 
                                                                distancias_de_puntos_a_recta_ejeZ[i+1], distancias_de_puntos_a_recta_ejeY[i+1], -distancias_de_puntos_a_recta_ejeX[i+1], 
                                                                r1 - .1, r2 - .1, color_colector_Rgba, 1, 
                                                                'Colector', 'y', math.pi / 2, name = 'ladoTramo2', trunco = False,
                                                                cota_final = cota_final, cota_inicial = cota_inicial, n = n)
            array_tramos_cilindro_mesh2.append(caras_lados_cilindro_colector3[0])
            
        caras_lados_rezZone = crear_cilindro_mesh3d(distancias_de_puntos_a_recta_ejeZ[i], distancias_de_puntos_a_recta_ejeY[i], -distancias_de_puntos_a_recta_ejeX[i],
                                                        distancias_de_puntos_a_recta_ejeZ[i+1], distancias_de_puntos_a_recta_ejeY[i+1], -distancias_de_puntos_a_recta_ejeX[i+1],
                                                        r3, r4, 'rgba(255, 66, 85, 1)', .25, 
                                                        'Zona no permitida para perforaciones', 'y', math.pi / 2, 
                                                        name = 'ladoRD', trunco = True, cota_final = cota_final, cota_inicial = cota_inicial, n = n)
        array_tramos_cilindors_redZone_mesh.append(caras_lados_rezZone[0])
        
        
        
    
    caras_lados_cilindro_colector = crear_cilindro_mesh3d(x1, y1, z1, x2, y2, z2, r1, r2, color_colector_Rgba, 1, 'Colector', 'y', math.pi / 2, name = 'ladoTramo1', trunco = False, cota_final = cota_final, cota_inicial = cota_inicial, n = n)
    caras_lados_cilindro_colector1 = crear_cilindro_mesh3d(x1, y1, z1, x2, y2, z2, r1 - .1, r2 - .1, color_colector_Rgba, 1, 'Colector', 'y', math.pi / 2, name = 'ladoTramo2', trunco = False, cota_final = cota_final, cota_inicial = cota_inicial, n = n)
    caras_lados_cilindro_redzone = crear_cilindro_mesh3d(x3, y3, z3, x4, y4, z4, r3, r4, 'rgba(255, 66, 85, 1)', .25, 'Zona no permitida para perforaciones', 'y', math.pi / 2, name = 'ladoRD', trunco = True, cota_final = cota_final, cota_inicial = cota_inicial, n = n)
    
    border_colector_C1 = go.Scatter3d(x = caras_lados_cilindro_colector[1][0], y = caras_lados_cilindro_colector[1][1], z = caras_lados_cilindro_colector[1][2], mode = 'lines', marker = dict(color = 'gray'), hovertemplate='-')
    border_colector_C2 = go.Scatter3d(x = caras_lados_cilindro_colector[2][0], y = caras_lados_cilindro_colector[2][1], z = caras_lados_cilindro_colector[2][2], mode = 'lines', marker = dict(color = 'gray'), hovertemplate='-')
    
    border_colector1_C1 = go.Scatter3d(x = caras_lados_cilindro_colector1[1][0], y = caras_lados_cilindro_colector1[1][1], z = caras_lados_cilindro_colector1[1][2], mode = 'lines', marker = dict(color = 'gray'), hovertemplate='-')
    border_colector1_C2 = go.Scatter3d(x = caras_lados_cilindro_colector1[2][0], y = caras_lados_cilindro_colector1[2][1], z = caras_lados_cilindro_colector1[2][2], mode = 'lines', marker = dict(color = 'gray'), hovertemplate='-')
    
    border_redzone_C1 = go.Scatter3d(x = caras_lados_cilindro_redzone[1][0], y = caras_lados_cilindro_redzone[1][1], z = caras_lados_cilindro_redzone[1][2], mode = 'lines', marker = dict(color = 'rgba(181, 0, 24, 1)'), hovertemplate='-')
    border_redzone_C2 = go.Scatter3d(x = caras_lados_cilindro_redzone[2][0], y = caras_lados_cilindro_redzone[2][1], z = caras_lados_cilindro_redzone[2][2], mode = 'lines', marker = dict(color = 'rgba(181, 0, 24, 1)'), hovertemplate='-')

    #DIBUJA COTA DE TERRENO
    
    puntos_plano_terreno = [(0, 0, cota_inicial[0][0]), 
                            (xf / 2, 15, (cota_inicial[0][0] + cota_final[0][0]) / 2), 
                            (xf, 0, cota_final[0][0])
                            ]
    
    max_dist_y = max(distancias_de_puntos_a_recta_ejeY)
    lado = 2*(puntos_plano_terreno[2][2] - (y_redzone_22 + 2*r4)) + max_dist_y*1.32

    def crear_plano_mesh3d(puntos_plano, color, opcacity, info, offset_Z):
        #Creo los 4 vertices del cuadrado que representan una porcion del plano que pasa por los puntos que definen al mismo 
        vertcices_planoArray = [(puntos_plano[0][0], puntos_plano[0][1] + (lado/2), puntos_plano[0][2] + offset_Z),
                                (puntos_plano[2][0], puntos_plano[2][1] + (lado/2), puntos_plano[2][2] + offset_Z),
                                (puntos_plano[0][0], puntos_plano[0][1] - (lado/2), puntos_plano[0][2] + offset_Z),
                                (puntos_plano[2][0], puntos_plano[2][1] - (lado/2), puntos_plano[2][2] + offset_Z)
                               ]
        
        x = [v[0] for v in vertcices_planoArray]
        y = [v[1] for v in vertcices_planoArray]
        z = [v[2] for v in vertcices_planoArray]
        i = [0, 2]
        j = [1, 3]
        k = [2, 1]
        return go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k, color=color, opacity=opcacity, lighting = dict(
            ambient = 0.5,
            diffuse = .1,
            specular = .5,
            roughness = 0.5,
            fresnel = .1,
            vertexnormalsepsilon = 1e-20,
            facenormalsepsilon = 1e-20
        ), 
        lightposition = dict(x = 0, y = 100, z = 100),
        intensitymode = 'cell',
        flatshading = True,
        hovertemplate=info)

    ###########################################
    # FUNCION PARA CREAR PRISMAS RECTOS       #
    ###########################################
    def crear_cube_mesh3d(puntos_plano, color, opcacity, info, extrude_distance):
        vertcicesPlanoArray = [(puntos_plano[0][0], puntos_plano[0][1] + (lado/2), puntos_plano[0][2]),
                               (puntos_plano[2][0], puntos_plano[2][1] + (lado/2), puntos_plano[2][2]),
                               (puntos_plano[0][0], puntos_plano[0][1] - (lado/2), puntos_plano[0][2]),
                               (puntos_plano[2][0], puntos_plano[2][1] - (lado/2), puntos_plano[2][2]),
                               (puntos_plano[0][0], puntos_plano[0][1] + (lado/2), puntos_plano[0][2] + extrude_distance),
                               (puntos_plano[2][0], puntos_plano[2][1] + (lado/2), puntos_plano[2][2] + extrude_distance),
                               (puntos_plano[0][0], puntos_plano[0][1] - (lado/2), puntos_plano[0][2] + extrude_distance),
                               (puntos_plano[2][0], puntos_plano[2][1] - (lado/2), puntos_plano[2][2] + extrude_distance)
                              ]
        x = [v[0] for v in vertcicesPlanoArray]
        y = [v[1] for v in vertcicesPlanoArray]
        z = [v[2] for v in vertcicesPlanoArray]
        i = [0, 2, 4, 6, 0, 4, 1, 7, 3, 2, 2, 4]
        j = [1, 3, 5, 7, 4, 5, 3, 3, 7, 6, 6, 0]
        k = [2, 1, 6, 5, 1, 1, 5, 5, 2, 7, 0, 6]
        return go.Mesh3d(x=x, y=y, z=z, i=i, j=j, k=k, color=color, opacity=opcacity, 
                        lightposition = dict(x = 0, y = 100, z = 100),
                        intensitymode = 'cell',
                        flatshading = True,
                        hovertemplate=info
                        )

    
    #####################################################
    ######## DIBUJO CARAS FRONTALES DE EL COLECTOR ######
    #####################################################
    
    xAux = caras_lados_cilindro_colector[0].x + caras_lados_cilindro_colector1[0].x
    yAux = caras_lados_cilindro_colector[0].y + caras_lados_cilindro_colector1[0].y
    zAux = caras_lados_cilindro_colector[0].z + caras_lados_cilindro_colector1[0].z

    iAux = np.concatenate((np.array(np.linspace(0, (n*2)-2, n)), np.array(np.linspace(1, (n*2)-1, n))))
    jAux = np.concatenate((np.array(np.linspace((n*2), (n*4)-2, n)), np.array(np.linspace((n*2)+1, (n*4)-1, n))))
    kAux = np.concatenate((np.array(np.linspace(2, (n*2), n)), np.array(np.linspace(3, (n*2)+1, n))))

    iAux1 = np.concatenate((np.linspace((n*2)+1, (n*4)-3, n-1), np.linspace((n*2), (n*4)-4, n-1)))#[62, 64, 66, 68]
    jAux1 = np.concatenate((np.linspace(3, (n*2)-1, n-1), np.linspace(2, (n*2)-2, n-1))) #[2, 4, 6, 8]
    kAux1 = np.concatenate((np.linspace((n*2)+3, (n*4)-1, n-1), np.linspace((n*2)+2, (n*4)-2, n-1))) #[64, 66, 68, 70]

    frente_colector = go.Mesh3d(x=xAux, y=yAux, z=zAux, i = np.concatenate((iAux1, iAux)), j = np.concatenate((jAux1, jAux)), k = np.concatenate((kAux1, kAux)), color = color_colector_Rgba, opacity = 1, flatshading = True, intensitymode = 'cell', hovertemplate='Colector')
    
    ##############################################
    #######    ANIMACION DE TUNELERA    ##########
    ##############################################
    #region ANIMACION
    frames_anim = None
    x_dis_esquina = 0
    profundidad_reltaiva = profundidad_tunelera
    anotacion_error = None
    pendiente2 = -(cota_final[0][0] - cota_inicial[0][0]) / (0 - xf) 
    def recta_terreno(X):
        """ recta que pasa los puntos de las cotas de terreno, cota_inicial y cota_final Devuelve la imagen de X en z"""
        return pendiente2 * X - (pendiente2*0) + (cota_inicial[0][0])
    #if (dis_esquina >= 0):
    x_dis_esquina = dis_esquina
    
    
    # pendiente = (Z1 - Z0) / (X1 - X0)
    # Z = mX - mX1 + Z1
    pendiente = (x4 - x3) / (y3 - z4) #esto esta bien, aunque parezca que no
    pendiente1 = ((x4+r4) - (x3+r3)) / (y3 - z4)
    
    
    def recta(X):  
        """ recta que pasa por los centros de las circunferencias del colector Devuelve la imagen de X en z"""
        return  pendiente * X - (pendiente*y3) + x3
    
    def recta1(X):
        """ recta que pasa por los puntos mas abajos(minimos) de la red zone Devuelve la imagen de X en z"""
        return pendiente1 * X - (pendiente1*y3) + (x3+r3) 
    

    
    #Radio de circunferencia para calcular interseccion
    radio_circ_temporal1 = (recta1(x_dis_esquina + diametro_tunelera/2)) - (recta(x_dis_esquina + diametro_tunelera/2))
    radio_circ_temporal2 = (recta1(x_dis_esquina - diametro_tunelera/2)) - (recta(x_dis_esquina - diametro_tunelera/2))
    
    profundidad_reltaiva = recta_terreno(x_dis_esquina) - (profundidad_tunelera)
    
    index_sub_tramo = seleccionar_sub_tramo(x_dis_esquina, distancias_de_puntos_a_recta_ejeX)
    
    x1_sub_t = distancias_de_puntos_a_recta_ejeX[index_sub_tramo]
    y1_sub_t = distancias_de_puntos_a_recta_ejeY[index_sub_tramo]
    x2_sub_t = distancias_de_puntos_a_recta_ejeX[index_sub_tramo + 1]
    y2_sub_t = distancias_de_puntos_a_recta_ejeY[index_sub_tramo + 1]
    pendiente_sub_tramo = (y2_sub_t - y1_sub_t) / (x2_sub_t - x1_sub_t)
    def recta_sub_tramo(X) -> float:
        return (pendiente_sub_tramo*X - pendiente_sub_tramo*x2_sub_t) + y2_sub_t
    
    

    #CILINDOR TEMPORAL es un cilindro que representa un corte del cilindro redZone con la altura del diametro de la tunelera
    cilindro_temporal_interseccion = crear_cilindro_mesh3d(recta(x_dis_esquina + diametro_tunelera/2), recta_sub_tramo(x_dis_esquina),  -(x_dis_esquina + diametro_tunelera/2), recta(x_dis_esquina - diametro_tunelera/2), recta_sub_tramo(x_dis_esquina),  -(x_dis_esquina - diametro_tunelera/2), radio_circ_temporal1, radio_circ_temporal2, 'orange', 1, 'temporal', 'y', math.pi / 2, 'name', False, cota_final = cota_final, cota_inicial = cota_inicial, n = n)
    Z_cota = np.concatenate((cilindro_temporal_interseccion[1][2], cilindro_temporal_interseccion[2][2])) #concatenacion de arrays con las coordenadas en Z de las circunferencias que forman el cildro
    Y_cota = np.concatenate((cilindro_temporal_interseccion[1][1], cilindro_temporal_interseccion[2][1])) #concatenacion de arrays con las coordenadas en Y de las circunferencias que forman el cildro

    cant_frames = 35
    switch_aux = 1 if profundidad_reltaiva > recta(x_dis_esquina) else -1
    
    #O(cantidad de vertices de circunferencia tunelera * cantidad de vertices de circunferencia cilindro rojo * 2) cantidad de iteraciones
    def interseccion_de_cilindros(cilindro_mesh) -> bool:
        """
            Devuelve True si el mesh pasado como parametro intersecta en algun punto al mesh de red zone
        """
        l = 0
        no_intersecta = True
        while l < len(cilindro_mesh[2][2]) and no_intersecta:
            i = 0
            while i < len(Z_cota) and no_intersecta:
                coord_vertice_enZ = cilindro_mesh[2][2][l] #vertice del cilindro tunelera
                coord_vertice_enY = cilindro_mesh[2][1][l]
                no_intersecta = (coord_vertice_enZ - Z_cota[i])*switch_aux > 0 or (coord_vertice_enY - Y_cota[i]) > 0
                i += 1
            l += 1
        return no_intersecta
    
  
    frames_anim = []
    
    
    #### ANIMACION DE CAMARA
    lado_cam_movment = 1 if x_dis_esquina > xf/2 else -1

    
    X_cam_path = np.linspace(1, 3.7*lado_cam_movment, cant_frames)
    Y_cam_path = np.linspace(3, 0.05, cant_frames)
    Z_cam_path = 0.01

    for t in range(cant_frames):
        frame_cam = dict(layout = dict(
            scene = dict(camera = dict(
                eye = dict(
                    x = X_cam_path[t], 
                    y = Y_cam_path[t], 
                    z = Z_cam_path), 
                center = dict(x = 0, y = 0, z = 0)))))
        frames_anim.append(frame_cam)
    

    k = 0
    paso = ((-lado/1.5) - (lado/1.5)) / cant_frames
    h = lado/1.5 
    ######################################## 
    ## Cilidro que representa la tunelera ## 
    ######################################## 
    dis_cat_op = math.sin(math.radians(-float(ang_tun)))*h
    
    cilindro_Frame = crear_cilindro_mesh3d(x_dis_esquina + dis_cat_op, -profundidad_reltaiva, lado/1.5, x_dis_esquina - dis_cat_op, -profundidad_reltaiva, h, diametro_tunelera/2, diametro_tunelera/2, 'rgba(204, 204, 204, .8)', 1, 'Tunelera', 'x', math.pi / 2, name='propTun', trunco = False, cota_final = cota_final, cota_inicial = cota_inicial, n = n)
    
    dis_cat_op_array_interpolation = np.linspace(-dis_cat_op, dis_cat_op, cant_frames+1)
    while k <= cant_frames and interseccion_de_cilindros(cilindro_Frame):
        frame = go.Frame(data = [cilindro_Frame[0]])
        #INTERPOLAR 0 a distanica cateto opuesto del triangulo formado por una recta perpendicular al subtramo, y la recta que representa a la tunelera (calular distancia) e ir sumando
        aux_sum = dis_cat_op_array_interpolation[k]
        cilindro_Frame = crear_cilindro_mesh3d(x_dis_esquina + dis_cat_op_array_interpolation[cant_frames], -profundidad_reltaiva, lado/1.5, x_dis_esquina - aux_sum, -profundidad_reltaiva, h, diametro_tunelera/2, diametro_tunelera/2, 'rgba(204, 204, 204, 8)', 1, 'Tunelera', 'x', math.pi / 2, name='propTun', trunco = False, cota_final = cota_final, cota_inicial = cota_inicial, n = n)
        frames_anim.append(frame)
        h += paso
        k += 1


    if k < cant_frames:
        punto_de_interseccion_tun_redzone = go.Scatter3d(x = [x_dis_esquina], y = [h - paso], z = [profundidad_reltaiva], marker=dict(color = 'red', symbol = 'x')) 
        anotacion_error = go.Layout( 
                    annotations = [go.layout.Annotation(x = 0, 
                                    y = .1, 
                                    text = 'Error!!!.<br>Interseccion de tunelera con zona <br>prohibida para perforaciones', 
                                    arrowcolor = "red",
                                    font = dict(size = 25),
                                    height = 100,
                                    width = 500, 
                                    valign = 'middle', 
                                    arrowsize = 1,
                                    align = 'center',
                                    arrowwidth = 1,
                                    arrowhead = 1,
                                    xanchor = 'left',
                                    bordercolor = 'rgba(220, 50, 50, 1)', 
                                    bgcolor = 'rgba(230, 0, 0, .3)',
                                    )
                                ]
                    )
                
        frame = go.Frame(data = [punto_de_interseccion_tun_redzone, cilindro_Frame[0]], layout = anotacion_error)
        frames_anim.append(frame)
    else:
        anotacion_exito = go.Layout( 
                    annotations = [go.layout.Annotation(x = 0, 
                                    y = .1, 
                                    text = 'Tunelera permitida', 
                                    arrowcolor = "green",
                                    font = dict(size = 25),
                                    height = 100,
                                    width = 500, 
                                    valign = 'middle', 
                                    align = 'center',
                                    arrowsize = 1,
                                    arrowwidth = 1,
                                    arrowhead = 1,
                                    xanchor = 'left',
                                    bordercolor = 'rgba(50, 200, 50, 1)', 
                                    bgcolor = 'rgba(50, 220, 50, .3)',

                                    )
                                    ]
                    )
                
        frame = go.Frame(data = [cilindro_Frame[0]], layout=anotacion_exito)
        frames_anim.append(frame)
            
    #endregion
            
    #########################################################
    #### CREO FIGURA 3D QUE CONTIENE TODAS LOS GRAFICOS #####
    #########################################################
    punto_fantasma = go.Scatter3d(x = [], y = [], z = []) #Por alguna razon al reproducir la animacion empieza a borrar los objetos de la lista data desde el principio, entonces creo puntos fantasmas para que borre esos

    array_string_text_direccion_agua = ["AA"]
    for i in range(1, len(array_tramos_cilindro_mesh)):
        array_string_text_direccion_agua.append(" ")
    array_string_text_direccion_agua.append("aa")
    
    direccion_agua_arrow = go.Scatter3d(x = distancias_de_puntos_a_recta_ejeX, y = distancias_de_puntos_a_recta_ejeY, z = np.linspace(zarriba, zabajo, len(distancias_de_puntos_a_recta_ejeX)),
                                   mode = 'lines+markers+text',
                                   line = dict(color='blue', width=3),
                                   text = array_string_text_direccion_agua,
                                   textposition = 'top center', 
                                   marker = dict(size = 2))
    
    dataFig = [punto_fantasma, punto_fantasma, crear_cube_mesh3d(puntos_plano_terreno, 'rgba(150, 150, 163, 1)', 1, 'Superficie', .18), crear_plano_mesh3d(puntos_plano_terreno, 'rgb(128, 128, 138)', 1, '', .183),
                frente_colector, direccion_agua_arrow,
                border_colector_C1, border_colector_C2, border_colector1_C1, border_colector1_C2]
    for i in range(0, len(array_tramos_cilindro_mesh)):
        dataFig.append(array_tramos_cilindro_mesh[i])
        if(i == 0 or i == len(array_tramos_cilindro_mesh)):
            dataFig.append(array_tramos_cilindro_mesh2[i])
        
        if(diametro_tunelera > 0):
            dataFig.append(array_tramos_cilindors_redZone_mesh[i])
    
    if(diametro_tunelera > 0):
        dataFig.append(border_redzone_C1)
        dataFig.append(border_redzone_C2)
    fig = go.Figure(data = dataFig, 
                            frames = frames_anim, 
                            layout = go.Layout(updatemenus = [dict(
                                                type = "buttons",
                                                buttons = [dict(label = "Play", 
                                                                method = "animate",
                                                                args = [None, dict(frame = dict(duration = 5, redraw = True),
                                                                                   transition = dict(duration = 4) 
                                                                                   )
                                                                        ]
                                                                )
                                                           ]
                                                )],
                                                #eye es la posicion y center el punto al que mira
                                                scene_camera = dict(eye=dict(x=4, y=4, z=.1))
                                                )
                    )
    if (profundidad_tunelera > 0):
        
        cilindro_tunelera = crear_cilindro_mesh3d(x_dis_esquina + dis_cat_op, -profundidad_reltaiva, lado/1.5, x_dis_esquina - dis_cat_op, -profundidad_reltaiva, -lado/1.5, diametro_tunelera/2, diametro_tunelera/2, 'rgba(204, 204, 204, .15)', 1, 'Tunelera', 'x', math.pi / 2, name='propTun', trunco = False, cota_final = cota_final, cota_inicial = cota_inicial, n = n)
        border_cilindro_tun = go.Scatter3d(x = cilindro_tunelera[1][0], y = cilindro_tunelera[1][1], z = cilindro_tunelera[1][2], mode = 'lines', marker = dict(color = 'black'))
        border_cilindro_tun1 = go.Scatter3d(x = cilindro_tunelera[2][0], y = cilindro_tunelera[2][1], z = cilindro_tunelera[2][2], mode = 'lines', marker = dict(color = 'black'))
        linea_trayectoria_tun = go.Scatter3d(x = [x_dis_esquina + dis_cat_op, x_dis_esquina - dis_cat_op], 
                                             y = [lado/1.5, -lado/1.5], 
                                             z = [profundidad_reltaiva, profundidad_reltaiva], 
                                             mode='lines+markers',  
                                             marker = dict(color = 'black', size = 5), 
                                             line = dict(dash = 'longdashdot'))
        fig.add_trace(cilindro_tunelera[0])
        fig.add_trace(border_cilindro_tun)
        fig.add_trace(border_cilindro_tun1)
        fig.add_trace(linea_trayectoria_tun)
      
    
    ##############################################
    #######    ANOTACIONES              ##########
    ##############################################

    anotaciones = []
    anotacion_tunelera = dict(x = x_dis_esquina, y = -lado/1.5, z = cota_inicial[0][0] - profundidad_tunelera, text = 'Camino para tunelera<br>Profundidad: ' + str(profundidad_tunelera) + 'm' + '<br>Diametro: ' + str(diametro_tunelera) + 'm',
                                bordercolor = '#969696', bgcolor = '#cccccc', align = 'left' )
    if(profundidad_tunelera > 0):
        anotaciones.append(anotacion_tunelera)
        
    fig.update_xaxes(layer = 'below traces')
    fig.update_yaxes(layer = 'below traces')


    fig.update_layout(
        title = dict(text ='Representación 3D', x = .5, y = .9, xanchor = 'center', yanchor = 'top'), 
        showlegend = False,
        scene = dict(annotations = anotaciones,
                     aspectmode='data',
                     xaxis_showgrid=False, yaxis_showgrid=False, zaxis_showgrid=False,
                     xaxis = dict(showticklabels = False),
                     yaxis = dict(showticklabels = False),
                     xaxis_title = " ",
                     yaxis_title = " ",
                     zaxis_title = 'Cota',
                     ),
        margin = {"r":5,"t":5,"l":5,"b":5}
       
    )
    fig.layout.height = 645
    

    #################################################################
    ##### CREA LA GRAFICA 2D ########################################
    #################################################################
    def make_graphic_2D():
        """Crea la grafica 2d que esta a la derecha en el dibujo """
        
        #COTA DE TERRENO
        terreno = go.Scatter(x = [0, xf], 
                             y = [cota_inicial[0][0], cota_final[0][0]], 
                             marker = dict(color = 'gray'), 
                             mode = 'lines',
                             name = 'Superficie')
        
        # DIBUJA TRAMO
        tramo_arriba = go.Scatter(x = [0, xf], 
                                  y = [zarriba+diam+espesor_arriba, zabajo+diam+espesor_arriba], 
                                  legendgroup = 'tramo',  
                                  marker = dict(color = color_colector_Hex), 
                                  mode = 'lines', 
                                  name = 'Colecotor', 
                                  hoverinfo = 'name')
        
        tramo_abajo =  go.Scatter(x = [0, xf], 
                                  y = [zarriba-espesor_abajo, zabajo-espesor_abajo], 
                                  legendgroup = 'tramo',  
                                  marker = dict(color = color_colector_Hex), 
                                  mode = 'lines',
                                  showlegend = False, 
                                  name = 'Colecotor',
                                  hoverinfo = 'name')
        
        def recta_tramo_arriba(X):
            m = ((zabajo+diam+espesor_arriba) - (zarriba+diam+espesor_arriba)) / xf
            #Ecuacion explicita
            return m*X + (zarriba+diam+espesor_arriba)

        def recta_tramo_abajo(X):
            m = ((zabajo-espesor_abajo) - (zarriba-espesor_abajo)) / xf
            return m*X + (zarriba-espesor_abajo)
        
        
        #RED ZONE
        lim_red_zone_abajo = go.Scatter(x = [0, xf], 
                                        y = [y_redzone_1, y_redzone_2], 
                                        legendgroup = 'redZone', 
                                        marker = dict(color = '#ff4255'), 
                                        mode = 'lines', 
                                        name = 'No permitido',
                                        hovertemplate='Zona no permitida para perforar',
                                        hoverinfo = 'name')
        
        lim_red_zone_arriba = go.Scatter(x = [0, xf], 
                                         y = [y_redzone_12, y_redzone_22], 
                                         legendgroup = 'redZone', 
                                         marker = dict(color = '#ff4255'), 
                                         mode = 'lines', 
                                         name = 'No permitido', 
                                         showlegend=False,
                                         hovertemplate='Zona no permitida para perforar', 
                                         hoverinfo = 'name')

        #FILL
        x = [0, xf, xf, 0]
        y = [zarriba+diam+espesor_arriba, zabajo+diam+espesor_arriba, zabajo-espesor_abajo, zarriba-espesor_abajo]
        fill_tramo_area = go.Scatter(x = x, y = y, mode = 'none', legendgroup = 'tramo', fill = 'toself', fillcolor = color_colector_Rgba, showlegend = False, hoverinfo='name')

        y = [zarriba - espesor_abajo, zabajo - espesor_abajo, y_redzone_2, y_redzone_1]
        fill_red_zone_arriba = go.Scatter(x = x, y = y, mode = 'none', legendgroup = 'redZone', fill = 'toself', fillcolor = 'rgba(255, 66, 85, .5)', showlegend = False, hovertemplate = 'Zona no permitida para perforar', hoverinfo = 'name', name = 'No permitido para perforacion')
        y = [y_redzone_12, y_redzone_22, zabajo + diam + espesor_arriba, zarriba + diam + espesor_arriba]
        fill_red_zone_abajo = go.Scatter(x = x, y = y, mode = 'none', legendgroup = 'redZone', fill = 'toself', fillcolor = 'rgba(255, 66, 85, .5)', showlegend = False, hovertemplate = 'Zona no permitida para perforar', hoverinfo = 'name', name = 'No permitido para perforacion')
        
        coords_center_tuneleras = [x_dis_esquina,  profundidad_reltaiva]
        fig = go.Figure( data=([ terreno, tramo_arriba, tramo_abajo, lim_red_zone_abajo, lim_red_zone_arriba, fill_tramo_area, fill_red_zone_arriba, fill_red_zone_abajo]))

        #Dibuja un circulo inscripto en el cuadrado con el vertice inferior izquiero en coords(x0, y0) y el vertice superior derecho (x1, y1)
        if(profundidad_tunelera > 0):
            fig.add_shape(type = "circle",
                xref = "x",
                yref = "y",
                x0 = coords_center_tuneleras[0] - diametro_tunelera/2 + dis_cat_op, y0 = coords_center_tuneleras[1] - diametro_tunelera/2, x1 = coords_center_tuneleras[0] + diametro_tunelera/2 + dis_cat_op, y1 = coords_center_tuneleras[1] + diametro_tunelera/2,
                line_color = "black",
                fillcolor = "PaleTurquoise",
            )
            x_line_circle = ((coords_center_tuneleras[0] - diametro_tunelera/2 + dis_cat_op) + (coords_center_tuneleras[0] + diametro_tunelera/2 + dis_cat_op)) / 2
            y_line_circle = coords_center_tuneleras[1] - diametro_tunelera/2
            
            if(float(ang_tun) != 0):
                fig.add_shape(type = "circle",
                    xref = "x",
                    yref = "y",
                    x0 = coords_center_tuneleras[0] - diametro_tunelera/2 - dis_cat_op, y0 = coords_center_tuneleras[1]-diametro_tunelera/2, x1 = coords_center_tuneleras[0] + diametro_tunelera/2 - dis_cat_op, y1 = coords_center_tuneleras[1] + diametro_tunelera/2,
                    line_color = "black",
                    fillcolor = "PaleTurquoise",
                )
                
                fig.add_trace(go.Scatter(
                    x = [x_line_circle, x_line_circle - (dis_cat_op*2), x_line_circle, x_line_circle - (dis_cat_op*2)],
                    y = [y_line_circle, y_line_circle, coords_center_tuneleras[1] + diametro_tunelera/2, coords_center_tuneleras[1] + diametro_tunelera/2],
                    mode = "lines",
                    line = dict(
                        color = "black",
                        width = 2,
                        dash = "dot",
                    ),
                    showlegend = False
                ))  
            #
            dis_centro_colector_terreno = abs(((recta_tramo_arriba(x_line_circle) + recta_tramo_abajo(x_line_circle))/2) - recta_terreno(x_line_circle))
            y_ = recta_tramo_arriba(x_line_circle) if profundidad_tunelera < dis_centro_colector_terreno else recta_tramo_abajo(x_line_circle)
            fig.add_trace(go.Scatter(
                x = [x_line_circle, x_line_circle],
                y = [y_line_circle, y_],
                mode = 'lines',
                line = dict(
                    color = 'black',
                    width = 2,
                    dash = 'dot'
                ),
                showlegend = False
            ))
            fig.add_annotation(text = str(abs(round(y_line_circle - y_, 3))) + 'm',
                  x = x_line_circle + .5, y = (y_line_circle + y_)/2, 
                  showarrow = False,
                  textangle = 0
            )
            fig.add_trace(go.Scatter(x = [dis_esquina, dis_esquina],
                                     y = [recta_terreno(dis_esquina), profundidad_reltaiva + diametro_tunelera/2],
                                     text=['', ''],
                                     mode = 'lines',
                                     dash = 'dot',
                                     line = dict(color = 'black', width = 2)))
            
            fig.add_annotation(text = str(round(abs((profundidad_reltaiva + diametro_tunelera/2) - recta_terreno(dis_esquina)), 2))+'m',
                            x = dis_esquina,
                            y = (recta_terreno(dis_esquina)+(profundidad_reltaiva + diametro_tunelera/2))/2,
                            textangle = 0)
                
        min_y = np.min([y_redzone_1, y_redzone_2, y_redzone_12, y_redzone_22])
        line_offset = 1
        #region linea de largo del colector
        fig.add_trace(go.Scatter(
            x = [0, xf/2, xf],
            y = [min_y - line_offset, min_y - line_offset, min_y - line_offset],
            text=['◄',
                str(round(xf, 2)) + 'm',
                '►'],
            mode = "lines+text",
            line = dict(
                color = "black",
                width = 2,
            ),
            textposition = 'top center',
            showlegend = False
        ))  
        #endregion

            
        fig.add_trace(go.Scatter(
            x = [0, xf/2, xf] if(datos[0][6] != 'IMP') else [0, 1, 2], # esto funciono pero no tengo muy claro el porque (por que cambia el texto de los puntos?)
            y = [zarriba, (zarriba+zabajo)/2, zabajo] if(datos[0][6] != 'IMP') else [0, 1, 2],
            mode = 'lines+text+markers',
            text = ['AA', '', 'aa'],
            marker = dict(symbol = "arrow", size = 15, angleref = "previous"),
            line = dict(color = 'blue', width = 2),
            textposition = 'top center',
            showlegend = False
        ))
        #region lineas de distancias a la red zone
        lin_V_offset = 4.5
        y_dis_redZone_1 = cota_inicial[0][0] - (cota_inicial[0][0] - y_redzone_12)
        y_dis_redZone_2 =  cota_final[0][0] - (cota_final[0][0] - y_redzone_22)
        y_dis_redZone_3 = cota_inicial[0][0] - (cota_inicial[0][0] - y_redzone_1)
        y_dis_redZone_4 =  cota_final[0][0] - (cota_final[0][0] - y_redzone_2)
        if(cota_inicial[0][0] - y_redzone_12 > 0):

            fig.add_trace(go.Scatter(
                x = [-lin_V_offset, -lin_V_offset],
                y = [cota_inicial[0][0], y_dis_redZone_1],
                text = ['-', '-'],
                mode = "lines+text",
                line = dict(color = "black", width = 2),
                showlegend = False
            ))  
            fig.add_annotation(text=str(round(cota_inicial[0][0] - y_redzone_12, 2)) + 'm',
                  x = -lin_V_offset - 2, y = (cota_inicial[0][0] + y_dis_redZone_1)/2, showarrow = False,
                  textangle = -90
            )

        if(cota_final[0][0] - y_redzone_22 > 0):
            fig.add_trace(go.Scatter(
                x = [xf + lin_V_offset, xf + lin_V_offset],
                y = [cota_final[0][0], y_dis_redZone_2],
                text=['-', '-'],
                mode = "lines+text",
                line = dict(color = "black", width = 2),
                showlegend = False
            )) 
            fig.add_annotation(text= str(round(cota_final[0][0] - y_redzone_22, 2))+'m',
                  x= xf + lin_V_offset + 2, y=(cota_final[0][0] + y_dis_redZone_2)/2, showarrow=False,
                  textangle = -90
            )
        
        if(cota_inicial[0][0] - y_redzone_1 > 0):
            fig.add_trace(go.Scatter(
                x = [-lin_V_offset*2, -lin_V_offset*2],
                y = [ cota_inicial[0][0], y_dis_redZone_3],
                text=['-', '-'],
                mode = "lines+text",
                line = dict(color = "black", width = 2),
                showlegend = False
            ))
            fig.add_annotation(text= str(round(cota_inicial[0][0] - y_redzone_1, 2))+'m',
                  x= (-lin_V_offset)*2 - 2, y=(cota_inicial[0][0] + y_dis_redZone_3)/2, showarrow=False,
                  textangle = -90
            )  

        if(cota_final[0][0] - y_redzone_2 > 0):
            fig.add_trace(go.Scatter(
                x = [xf + lin_V_offset*2, xf + lin_V_offset*2],
                y = [cota_final[0][0], y_dis_redZone_4],
                text=['-', '-'],
                mode="lines+text",
                line = dict(color = "black", width = 2),
                showlegend = False
            ))  
            fig.add_annotation(text=  str(round(cota_final[0][0] - y_redzone_2, 2))+'m',
                  x=  xf + (lin_V_offset)*2 + 2, y = (cota_final[0][0] + y_dis_redZone_4)/2, showarrow=False,
                  textangle = -90
            )  
            
            fig.add_annotation(text = 'Zampeado: ' + str(round(recta_zampeado(dis_esquina), 2)),
                x = dis_esquina,
                y = recta_terreno(dis_esquina)-.15)
        #endregion
        fig.update_layout(scene_xaxis_visible = False, 
                          scene_yaxis_visible = False, 
                          title = dict(text='Perfil longitudinal', 
                                       y = .9, 
                                       x = .5,
                                       xanchor = 'center',
                                       yanchor = 'top'), 
                          showlegend = True, 
                          scene = dict(aspectmode = 'cube'),  
                          xaxis_title = "",
                          yaxis_title = "Cota", 
                          autosize = True)
        fig['layout']['yaxis'].update(autorange = True)
        return fig

    pendiente_tramo_porcentaje = round((abs(cota_final[0][0] - cota_inicial[0][0]) / xf) * 100, 2)
    datos_to_tabla = [[cota_inicial[0][0], zarriba, datos[0][2], pendiente_tramo_porcentaje, coords_puntos_tapas[2], coords_puntos_tapas[3], cota_inicial[0][1]],
                      [cota_final[0][0], zabajo, datos[0][3], pendiente_tramo_porcentaje, coords_puntos_tapas[0], coords_puntos_tapas[1], cota_final[0][1]],
                      [xf, datos[0][0], datos[0][1]]]

    
    

    return [fig, make_graphic_2D(), datos_to_tabla]


################################################
#### PARTE DE DASH FRAMEWORK PARA HACERLO WEB ##
################################################

#region DASH

init_graph = create_graph(1, 0, 0, dis_esquina = 0, ang_tun = 0)

alert1 = dbc.Alert(
    [
        dbc.Row([dbc.Col(html.H4("ERROR", className="alert-heading")),
                 dbc.Col(html.I(className="bi bi-x-octagon-fill me-3")),
                ], justify='around'),
        html.P(
            'Datos faltantes en el servidor para poder dibujar'
        ),
        html.Hr(),
        html.P(
            'Falta dato de cota de aguas arriba',
            className="mb-0",
        ),
    ], 
    color = "danger",
    dismissable = True
)

alert2 = dbc.Alert(
    [
        dbc.Row([ dbc.Col(html.H4("ERROR", className="alert-heading")),
                 dbc.Col(html.I(className="bi bi-x-octagon-fill me-2")),
                ], justify='around'),
        html.P(
            'Datos faltantes en el servidor para poder dibujar'
        ),
        html.Hr(),
        html.P(
            'Falta dato de cota de aguas abajo',
            className="mb-1",
        ),
    ], 
    color="danger",
    dismissable = True
)

alert3 = dbc.Alert(
    [
        dbc.Row([dbc.Col(html.H4("ERROR", className="alert-heading")),
                 dbc.Col(html.I(className="bi bi-x-octagon-fill me-3")),
                ], justify='around'),
        html.P(
            'Datos faltantes en el servidor para poder dibujar'
        ),
        html.Hr(),
        html.P(
            'Faltan dato de cota de aguas abajo y aguas arriba',
            className="mb-2",
        ),
    ], 
    color="danger",
    dismissable = True
)

image_card = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H4("INPUTS", className="card-title"),
                html.H6("Datos de entrada:", className="card-text"),
                html.Hr(),
                html.H6('id de Tramo',className='label'),
                dcc.Input(value = '1', type = 'number', id = 'idT', className='Input'),
                html.H6('Diametro tunelera(m)', className='label'),
                dcc.Input(value = '0', type = 'number', id = 'diametroTun', className='Input'),
                html.H6('Profundidad Tunelera(m)', className='label'),
                dcc.Input(value = '0', type = 'number', id = 'profundidadTun', className='Input'),
                html.H6('distancia a punto singular Aguas Arriba (m)', className='label'),
                dcc.Input(value = '0', type = 'number', id = 'disEsq', className='Input'),
                html.H6('ángulo de tunuelera en planta (grados)', className='labelAngle'),
                dcc.Input(value = '0', type = 'number', id = 'angTun', className='Input'),
                html.Button('Generar gráfico', id='button', n_clicks = 0, className='Button'),
                html.Hr(),
                html.Div(id="the_alert", children=[]),
            ], 
        ),
        dbc.CardBody(
            [
                html.H5('COMO USAR'),
                html.P('1-Ingrese todos los datos en la zona de inputs'),
                html.P('2-Clické en el boton de generar grafico'),
                html.P('3-Clicke el boton Play para ver la animacion y resultado de la tunelera'),
                html.Hr(),
                html.H5('Como moverse en la grafica 3D'),
                html.P('🖱 manteniendo click izquierdo y arrastrando roto en el espacio '),
                html.P('🖱 manteniendo click derecho y arrastro para panear '),
                html.P('🔎 con la rueda del raton hago zoom in y zoom out')
            ]
            )
    ],
    color="light",
)

graph_card = dbc.Card(
    [
        dbc.CardBody(
            [
                html.H4("GRAFICAS", className="card-title", style={"text-align": "center"}),
                dcc.Loading(
                    id = "loading-1",
                    type = "graph",
                    children = html.Div(id="loading-output-1"),
                    fullscreen = True,
                    className = 'Loading',
                    debug = False
                ),
                html.Div([
                    dcc.Graph(figure = init_graph[0], id = 'graph3D'),
                    # html.Div(id='current-camera-coordinates'),
                    dcc.Graph(figure = init_graph[1], id = 'graph2D'),
                    dcc.Graph(figure = make_map_2(csv_data_tramos, 1, 0, 0), id = '_map'),
                    dbc.CardBody(
                        [
                            html.H6('DATOS unidades: utm 84-21s Wharton'),
                            html.Div(id = 'tabla', children=[])
                        
                        ], id = 'Tabla')
                    ], id = 'Graficos'),
                
            ]
        ),
    ],
    color="light",
)

modal = html.Div(
    [
        dbc.Modal(
            [
                dbc.ModalHeader(dbc.ModalTitle("Advertencia!!")),
                dbc.ModalBody("Tramo posiblemente mal mapeado, notificar a técnicos"),
                dbc.ModalFooter(
                    dbc.Button(
                        "Close", id="close", className="ms-auto", n_clicks=0
                    )
                ),
            ],
            id="modal",
            centered=True,
            is_open=False,
        ),
    ]
)




# ************************************************************************************************************************************************
app.layout = html.Div([
    dbc.Row([dbc.Col(image_card, width = 2), dbc.Col(graph_card, width = 10), modal], justify = "around")
], id = 'MainLabel', )
# ************************************************************************************************************************************************

@app.callback(
    [
    Output('loading-output-1', 'children'),
    Output('graph3D', 'figure'),
    Output('graph2D', 'figure'),
    Output('tabla', 'children'),
    Output('_map', 'figure'),
    Output('the_alert', 'children'),],
    State('idT', 'value'),
    State('diametroTun', 'value'),
    State('profundidadTun', 'value'),
    State('disEsq', 'value'),
    State('angTun', 'value'),
    Input('button', 'n_clicks'),
)
def update_figure(selected_ID, diametro_tunelera, profundidad_tunelera, dis_esquina, ang_tun, n_clicks):
    fig = create_graph(selected_ID, float(diametro_tunelera), float(profundidad_tunelera), float(dis_esquina), ang_tun)

    
    #_map = make_map(csv_data_tramos, selected_ID, dis_esquina)
    _map = make_map_2(csv_data_tramos, abs(int(selected_ID)), dis_esq = float(dis_esquina), ang_tun = ang_tun)
    if  (app.server.my_variable != 'Danger!!'):
        fig[0].update_layout(transition_duration = 500)
        fig[1].update_layout(transition_duration = 500)
        _map.update_layout(transition_duration = 500)

    else:
        my_variable = app.server.danger_type
        alert = None
        if(my_variable == 'Danger01'):
            alert = alert1
        elif(my_variable == 'Danger02'):
            alert = alert2
        else:
            alert = alert3
        return dash.no_update, dash.no_update, dash.no_update, dash.no_update, alert
    
    datos_tabla = fig[2]
    table_data = pd.DataFrame.from_dict(
        {
            '-': ['Cota de terreno', 'Zampeado', 'Coord X', 'Coord Y', 'id Punto'],
            'AA': [str(datos_tabla[0][0]), str(datos_tabla[0][1]), str(round(datos_tabla[0][4], 2)), str(round(datos_tabla[0][5], 2)), str(datos_tabla[0][6])],
            'aa': [str(datos_tabla[1][0]), str(datos_tabla[1][1]), str(round(datos_tabla[1][4], 2)), str(round(datos_tabla[1][5], 2)), str(datos_tabla[1][6])],
        }
    )
    
    table_data2 = pd.DataFrame.from_dict(
        {
            '-': ['Longitud(m)', 'Tipo tramo', 'Tipo seccion', 'Seccion', 'Pendiente'],
            '--': [str(round(datos_tabla[2][0])), str(datos_tabla[2][1]), str(datos_tabla[2][2]), str(datos_tabla[0][2]), str(datos_tabla[0][3]),]
        }
    )
    
    tabla_res = html.Div(
        [
            dash_table.DataTable(
                data = table_data.to_dict('records'),
                columns = [{'id': x, 'name': x} for x in table_data.columns],
                style_cell={'textAlign': 'center'},
            ),
            dash_table.DataTable(
                data = table_data2.to_dict('records'),
                columns = [{'id': x, 'name': x} for x in table_data2.columns],
                style_cell={'textAlign': 'center'},
            )
        ]
    )

    
    return None, fig[0], fig[1], tabla_res, _map, None


@app.callback(
    Output("modal", "is_open"),
    [Input("button", "n_clicks"), Input("close", "n_clicks")],
    [State("modal", "is_open")],
)
def toggle_modal(n1, n2, is_open):
    if not app.server.many_points and (n1 or n2):
        return not is_open
    return is_open
if __name__ == '__main__':
    app.run_server(debug = True, port='8080')

#endregion

