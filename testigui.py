from nicegui import ui, app
from source.ModbusDriver import modbus

# Moottorit jotka ei ole käytössä
puuttuvat_moottorit = [2,5,7]

# moottoritiedot
moottorit = [
    {'id': i, 'virta': 0, 'asetus': 0, 'jannite':0,'taajuus':0,'pwm':0}
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

ui.button('PYSÄYTÄ OHJELMA', color='red', on_click=kysy_vahvistus).style('font-size: 20px; margin: 10px;')
# Luo jokaiselle käytössä olevalle moottorille oman kortin jossa on moottorin tiedot ja moottorin käyttönapit
def luo_moottori_ikkuna(moottori):
    with ui.card().style('padding: 20px; min-width: 200px; margin:5px'):
        # Moottorin tunnus
        ui.label(f'Moottori {moottori["id"]}').style('font-weight: bold; font-size: 20px; text-align: center;')
        
        # Nykyinen virta
        virta_label = ui.label(f'Virta: {moottori["virta"]}')
        # nykyinen jännite
        jannite_label = ui.label(f'Jännite: {moottori["jannite"]}')
        # Nykyinen asetusarvo
        asetus_label = ui.label(f'Asetus: {moottori["asetus"]}')
        
        # Syöttökenttä ja nappi
        input_field = ui.input(placeholder='Uusi asetus')

        
       # Funktio lulee moottorin nopeus arvon ja asettaa moottorille halutun nopeuden      
        def validoi_asetus():
            try:
                arvo = float(input_field.value)
                moottori['asetus'] = arvo
                asetus_label.text = f'Asetus [0-1000]: {arvo}'
                ui.notify(f'Moottori {moottori["id"]} asetettu: {arvo}')
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
            asetus_label.text = "Asetus: 0"   
        
        with ui.button_group():
            ui.button('Eteen', on_click=pyorita_eteen)
            ui.button('Taakse',on_click=pyorita_taakse)
            ui.button("SEIS",color="red", on_click=pysayta)
        # Reaaliaikainen päivitys
        def paivita_arvot():
            #
            arvot = modbus.read_status(moottori['id'])
            moottori['virta'] = arvot['current_A']
            moottori['jannite'] = arvot['voltage_V']
            virta_label.text = f'Virta: {moottori["virta"]}'
            jannite_label.text = f'Jännite: {moottori["jannite"]}'
        
        ui.timer(1.0, paivita_arvot)  # päivittää 1 sekunnin välein

# Luo kaksi riviä: ensimmäinen 1,2,3 ja toinen 4,5,6
# Skipataan puuttuvat moottori
per_rivi = 2

with ui.column():
    for rivi in range(0, len(moottorit), per_rivi):
        with ui.row():
            for moottori in moottorit[rivi:rivi + per_rivi]:
                luo_moottori_ikkuna(moottori)



#ui.run(title='Moottoriohjaus - Reaaliaikainen')
ui.run(host="0.0.0.0",port=8080, title="Moottoreiden testaus")

