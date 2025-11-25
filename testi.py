# Ohjelma jolla on tarkoitus testata moottorien toimintaa
# voidaan käyttää vian etsintään ja toimintojen testaamiseen

import sys
import select
import time


from source.ModbusDriver import modbus

def aja_moottoria () -> None:
    """ Voidaan testi jolla voidaan ajaa moottoria tietyllä nopeudella haluttuun suuntaan
    """  
    print("Aja haluamaasi moottoria")
    moottori = int(input("Anna moottorin osoite [0-6] (0 kaikki moottorit): "))
    nopeus = int(input("Anna moottorille nopeus [0-1000]: "))
    suunta = int(input("Anna suunta [0 eteen tai 1 taakse]: "))

    modbus.set_direction(moottori,suunta)
    modbus.set_speed(moottori,nopeus)

def lue_virta(Moottori: int=1 ) -> str:
    """Luetaan virta halutulta moottorilta"""
    return modbus.read_current(Moottori)
    

def main():
    
    
    while True:

        
        print("""
          Aja haluamaasi moottoria syöttämällä 1
          Lue haluamasi moottorin virta-arvo syöttämällä 2""")
        kasky = input('Lopeta syöttämällä "Q": ' )
        if kasky == "Q" or kasky == "q":
            modbus.set_speed(0,0) # Pysäytetään kaikki moottorit
            print('Ohjelma lopetetaan')
            break
       
        elif kasky == "1":
            aja_moottoria()
        
        elif kasky =="2":
            print("Lue virta moottorilta")
            moottori = int(input("Anna moottorin osoite [1-6]: "))
            while True:
                print("Lopeta painamalla Enter")
                virta = lue_virta(moottori)
                print(f"Moottorin virta: {virta}A \n")
                time.sleep(0.5)

                # Jos käyttäjä painoi Enter, lopetetaan VAIN tämä silmukka
                if sys.stdin in select.select([sys.stdin], [], [], 0)[0]:
                    sys.stdin.read(1)  # luetaan yksi merkki pois puskurista
                    print("Tulostus pysäytetty.\n")
                    break
            

    


if __name__ == "__main__":
    main()