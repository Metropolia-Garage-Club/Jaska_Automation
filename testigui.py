from nicegui import ui, app
from source.ModbusDriver import modbus

# Moottorit jotka ei ole käytössä
puuttuvat_moottorit = [2,5,7]

# moottoritiedot
moottorit = [
    {'id': i, 'virta': 0, 'asetus': 0, 'jannite':0,'taajuus':0,'pwm':0, 'jarru_virta':0, 'suunta':"",'rpm':0}
    for i in range(1, 7)
    if i not in puuttuvat_moottorit
]


def sammuta():
    modbus.set_speed(0.0)
    app.shutdown()

def kysy_vahvistus():
    with ui.dialog() as dialog, ui.card():
        ui.label('Haluatko varmasti pysäyttää ohjelman?')
        ui.button('Kyllä', color='red', on_click=sammuta)
        ui.button('Peruuta', on_click=dialog.close)
    dialog.open()
def suunta2str(io:int):
    if io == 0:
        return "Eteen"
    elif io== 1:
        return "Taakse"
    else:
        return ""
ui.button('PYSÄYTÄ OHJELMA', color='red', on_click=kysy_vahvistus).style('font-size: 20px; margin: 10px;')
# Luo jokaiselle käytössä olevalle moottorille oman kortin jossa on moottorin tiedot ja moottorin käyttönapit
def luo_moottori_ikkuna(moottori):
    with ui.card().style('padding: 20px; min-width: 200px; margin:5px'):
        # Moottorin tunnus
        ui.label(f'Moottori {moottori["id"]}').style('font-weight: bold; font-size: 20px; text-align: center; margin: auto;')
        
        # Nykyinen virta
        # -------- GAUGE / VIISARIMITTARI --------
        virta_mittari_options = {
    "series": [{
        "type": "gauge",
        "min": 0,
        "max": 60,

        "axisLine": {
            "lineStyle": {
                "width": 12,
                "color": [
                    [0.2, "#4caf50"],   # vihreä
                    [0.8, "#ffeb3b"],   # keltainen
                    [1.0, "#f44336"]    # punainen
                ]
            }
        },

        "axisLabel": {
            "interval":10,
            "color": "#000000",
            "fontSize": 7
        
        },

        "progress": {"show": False},
        "detail": {"valueAnimation": True, "formatter": "{value}A", "fontSize": 15},
        "data": [{"value": 0}]
    }]
}

        kierros_mittari_options = {
            "series": [{
                "type": "gauge",
                "min": 0,
                "max": 800,
                "progress": {"show": True},
                "detail": {"valueAnimation": True, "formatter": "{value}" ,"fontSize": 10},
                "data": [{"value": 0}],
                "axisLabel": {
                            "interval":20,
                            "color": "#000000",
                            "fontSize": 7
                            },
                
            }]
        }
        with ui.row().style("gap: 20px; justify-content: center"):
                Virta_mittari = ui.echart(options=virta_mittari_options)\
                    .style("height: 180px; width: 180px")
                kierros_mittari = ui.echart(options=kierros_mittari_options)\
                    .style("height: 180px; width: 180px")
                
        #virta_label = ui.label(f'Virta: {moottori["virta"]}A')
        # nykyinen jännite
        ui.label("RPM").style("position:absolute; right:90px; top: 200px; font-weight: bold")
        ui.label("VIRTA").style("position:absolute; left:90px; top: 200px; font-weight: bold")
        jannite_label = ui.label(f'Jännite: {moottori["jannite"]}V')
        #taajuus_label = ui.label(f'Taajuus: {moottori["taajuus"]}Hz')
        pwm_label = ui.label(f'PWM: {moottori["pwm"]}')
        jarru_virta_label = ui.label(f'Jarru Virta: {moottori["jarru_virta"]}A')
        
        suunta_label = ui.label(f'Suunta: {moottori["suunta"]}')
        taajuus_label = ui.label(f'RPM: {moottori["taajuus"]}')
        # Nykyinen asetusarvo
        asetus_label = ui.label(f'Asetus [0-1000]: {moottori["asetus"]}')
        # Syöttökenttä ja nappi
        input_field = ui.input(placeholder='Uusi asetus')

        
       # Funktio lulee moottorin nopeus arvon ja asettaa moottorille halutun nopeuden      
        def validoi_asetus():
            try:
                arvo = float(input_field.value)
                moottori['asetus'] = arvo
                asetus_label.text = f'Asetus [0-1000]: {arvo}'
                ui.notify(f'Moottori {moottori["id"]} asetettu: {arvo}',position='center')
                modbus.set_speed(moottori["id"],arvo)
            except ValueError:
                ui.notify('Virheellinen arvo!', color='red')
        #määrittää moottorin pyörimis suunnan eteen
        def pyorita_eteen():
            modbus.set_direction(moottori["id"],0)
            validoi_asetus()
        #määrittää moottorin pyörimis suunnan taakse
        def pyorita_taakse():
            modbus.set_direction(moottori["id"],1) 
            validoi_asetus()
        #pysäyttää moottorin
        def pysayta():
            modbus.set_speed(moottori["id"],0)
            ui.notify(f"Moottori {moottori['id']} pysäytetty")
            asetus_label.text = "Asetus [0-1000]: 0"   
        
        with ui.button_group():
            ui.button('Eteen', on_click=pyorita_eteen)
            ui.button('Taakse',on_click=pyorita_taakse)
            ui.button("SEIS",color="red", on_click=pysayta)
        # Reaaliaikainen päivitys
        def paivita_arvot():
            #Luetaan moottorin arvot ja siirretään ne talteen
            try:
                arvot = modbus.read_status(moottori['id'])
                moottori['virta'] = arvot['current_A']
                moottori['jannite'] = arvot['voltage_V']
                moottori['taajuus'] = arvot['frequency_Hz']
                moottori['jarru_virta'] = arvot['brake_current_A']
                moottori['pwm'] = arvot['pwm']
                moottori['suunta'] = arvot['dir']
                moottori['rpm'] = 60*moottori['taajuus']/15
                #virta_label.text = f'Virta: {moottori["virta"]}A'
                jannite_label.text = f'Jännite: {moottori["jannite"]}V'
                #taajuus_label.text = f'Taajuus: {moottori["taajuus"]}Hz'
                pwm_label.text = f'PWM: {moottori["pwm"]}'
                jarru_virta_label.text = f'Jarru virta: {moottori["jarru_virta"]}A'
                Virta_mittari.options['series'][0]['data'][0]['value'] = moottori['virta']
                Virta_mittari.update()            
                kierros_mittari.options['series'][0]['data'][0]['value'] = moottori['rpm']
                kierros_mittari.update()
                suunta_label.text = f'Suunta: {moottori["suunta"]}'
                taajuus_label.text = f'Taajuus: {moottori["taajuus"]} Hz'
            except Exception as e:
                print(f"Virhe moottorin {moottori['id']} luennassa: {e}")
        ui.timer(1.0, paivita_arvot)  # päivittää 1 sekunnin välein

# Luo kaksi riviä: ensimmäinen 1,2,3 ja toinen 4,5,6
# Skipataan puuttuvat moottori
per_rivi = 2
with ui.column():
    for rivi in range(0, len(moottorit), per_rivi):
        with ui.row():
            for moottori in moottorit[rivi:rivi + per_rivi]:
                luo_moottori_ikkuna(moottori)

ui.button("Pysäytä Kaikki moottorit",color='red', on_click= lambda: modbus.set_speed(0,0)).style('font-size: 15px')

#ui.run(title='Moottoriohjaus - Reaaliaikainen')
ui.run(host="0.0.0.0",port=8080, title="Moottoreiden testaus")

