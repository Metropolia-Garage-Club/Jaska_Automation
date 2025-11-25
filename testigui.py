from nicegui import ui
from source.ModbusDriver import modbus

# Moottorit jotka ei ole käytössä
puuttuvat_moottorit = [2,5,7]

# moottoritiedot
moottorit = [
    {'id': i, 'virta': 0, 'asetus': 0}
    for i in range(1, 7)
    if i not in puuttuvat_moottorit
]


def luo_moottori_ikkuna(moottori):
    with ui.card().style('padding: 20px; min-width: 200px; margin:5px'):
        # Moottorin tunnus
        ui.label(f'Moottori {moottori["id"]}').style('font-weight: bold; font-size: 20px; text-align: center;')
        
        # Nykyinen nopeus
        nopeus_label = ui.label(f'Nopeus: {moottori["virta"]}')
        
        # Nykyinen asetusarvo
        asetus_label = ui.label(f'Asetus: {moottori["asetus"]}')
        
        # Syöttökenttä ja nappi
        input_field = ui.input(placeholder='Uusi asetus')

        
            
        def validoi_asetus():
            try:
                arvo = float(input_field.value)
                moottori['asetus'] = arvo
                asetus_label.text = f'Asetus: {arvo}'
                ui.notify(f'Moottori {moottori["id"]} asetettu: {arvo}')
                modbus.set_speed(moottori["id"],arvo)
            except ValueError:
                ui.notify('Virheellinen arvo!', color='red')
        
        def pyorita_eteen():
            modbus.set_direction(moottori["id"],0)
            validoi_asetus()
        
        def pyorita_taakse():
            modbus.set_direction(moottori["id"],1) 
            validoi_asetus()

        def pysayta():
            modbus.set_speed(moottori["id"],0)
            ui.notify(f"Moottori {moottori['id']} pysäytetty")
            asetus_label.text = "Asetus: 0"   
        with ui.button_group():
            ui.button('Eteen', on_click=pyorita_eteen)
            ui.button('Taakse',on_click=pyorita_taakse)
            ui.button("SEIS",color="red", on_click=pysayta)
        # Reaaliaikainen päivitys
        def paivita_virta():
            #
            moottori['virta'] = modbus.read_current(moottori["id"])
            nopeus_label.text = f'Virta: {moottori["virta"]}'
        
        ui.timer(1.0, paivita_virta)  # päivittää 1 sekunnin välein

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

