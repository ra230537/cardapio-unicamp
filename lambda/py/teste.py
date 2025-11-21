from urllib import response
import requests
from bs4 import BeautifulSoup
import datetime
def get_cardapio(date):
    format_date = date.strftime('%Y-%m-%d')
    url = f'https://sistemas.prefeitura.unicamp.br/apps/cardapio/index.php?d={format_date}'

    response = requests.get(url)
    return response


'''
Extrai o menu do HTML retornado pela requisição
Retorna um dicionário com as refeições
Almoco, Almoco_veg, Jantar, Jantar_veg
Titulo
Prato principal
Acompanhamento
Salada
Sobremesa
'''
def extract_menu(response):
    soup = BeautifulSoup(response.text, 'html.parser')

    # Extrair todas as seções do cardápio (Almoço, Jantar, etc)
    sections = soup.find_all('div', class_='menu-section')
    dict_menu = {'Almoco': [], 'Almoco_veg': [], 'Jantar': [], 'Jantar_veg': []}
    for section in sections:
        title_tag = section.find('h2', class_='menu-section-title')
        title = title_tag.get_text(strip=True) + '\n'
        # print(f"=== {title} ===")

        item_name = section.find('div', class_='menu-item-name')
        if item_name:
            name_desc = item_name.get_text(strip=True) + '\n'
            # print(f"Prato principal: {item_name.get_text(strip=True)}") 

        item_desc = section.find('div', class_='menu-item-description')
        if item_desc:
            desc_text = item_desc.get_text(separator="\n", strip=True) + '\n'
            # print(f"Descrição:\n{desc_text}\n")
        refeicao = ''
        match title.strip():
            case 'Almoço':
                refeicao = 'Almoco'
            case 'Almoço Vegano':
                refeicao = 'Almoco_veg'
            case 'Jantar':
                refeicao = 'Jantar'
            case 'Jantar Vegano':
                refeicao = 'Jantar_veg'
        dict_menu[refeicao].append(title)
        dict_menu[refeicao].append(name_desc)
        dict_menu[refeicao].append(desc_text)
    
    return filter_menu(dict_menu)
def filter_menu(extracted_menu):
    for key, value in extracted_menu.items():
        items_list = []
        for item in value:
            splitted_item = item.replace('\n', '#').split('#')
            items_list.extend(splitted_item)
        items_list = list(filter(lambda x: x != '', items_list))
        items_list = list(filter(lambda x: 'Observações:'.upper() not in x.upper(), items_list))
        items_list = list(filter(lambda x: 'Glúten'.upper() not in x.upper(), items_list))
        items_list = list(filter(lambda x: 'cardápio vegano será servido'.upper() not in x.upper(), items_list))
        items_list = list(filter(lambda x: 'ARROZ E FEIJÃO'.upper() not in x.upper(), items_list))
        items_list = list(filter(lambda x: 'ARROZ INTEGRAL E FEIJÃO'.upper() not in x.upper(), items_list))
        items_list = list(filter(lambda x: 'REFRESCO'.upper() not in x.upper(), items_list))
        extracted_menu[key] = items_list
    return extracted_menu
html = get_cardapio(datetime.datetime.now()+datetime.timedelta(days=0))
extracted_menu = extract_menu(html)
print(extracted_menu)

def print_menu_phrase(extracted_menu, key):
    items = extracted_menu[key]
    refeicao = items[0]
    prato_principal = items[1]
    acompanhamentos = items[2]
    salada = items[3]
    sobremesa = items[4]
    contem_lactose = items[5]

    # Monta a frase
    frase = (
        f"No {refeicao}, o prato principal é {prato_principal}, "
        f"acompanhado de {acompanhamentos}, "
        f"salada de {salada}, "
        f"e de sobremesa tem {sobremesa}. "
        f"{contem_lactose}."
    )
    print(frase)
    return frase
