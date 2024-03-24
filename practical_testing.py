import keyboard
import time
from tqdm import tqdm



def main():

    cmds=[
        '$register',
        '$profile',
        '$profile uoifnbsiuef',
    

        '$buy flasteh 0.1',
        '$yes',
        '$buy 2 flasteh',
        '$sell 3 justman',
        '$sell flasteh 0.1',
        '$no',

        '$buy mrekk 4',
        '$buy flasteh 9999999',
        '$sell justman 2',
        '$sell flasteh all',
        '$yes',
        '$buy "chokbar de bz" 0.15435',
        '$buy Carbone 0.3',
        '$y',
        '$buy justman sefuosebhfnoi',
        
        '$profile @Antoin',

        '$balance',
        '$balance iufseiub3 2 sfe iuzdq',
        '$balance mihate',

        '$market',
        '$market -v 44',
        '$market -d 2 -h 3',
        '$market -d -2',
        '$market -h 0',
        '$market -h 5 -sortby evolution',
        '$market -h 5 -sortby dividend',
        '$market -h 5 -sortby gdrtdrgsdegrf',
        '$market -h 1 -tdrgsdegrf',

        '$lb',
        '$lb -oisrdefoisef',

        '$stock flasteh',
        '$stock mrekk',
        '$stock @Antoi',
        '$stock flasteh -d 2',
        '$stock flasteh -h 1',
        '$stock flasteh -h isudfsidbuf',
        '$stock flasteh -d -fsidbuf',
        '$stock flasteh -fsidbuf',
        
        '$pingmeif',
        '$pingmeif flasteh > 10',
        '$pingmeif flasteh>3',
        '$pingmeif fsefhuehuife',       
        ]
    print('click on the right channel...')
    for c in cmds:
        time.sleep(5)
        keyboard.write(c)
        time.sleep(0.2)
        keyboard.press_and_release('enter')
        time.sleep(0.2)
        keyboard.press_and_release('enter')



if __name__ == '__main__':
    main()