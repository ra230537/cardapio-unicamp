# -*- coding: utf-8 -*-

# This sample demonstrates handling intents from an Alexa skill using the Alexa Skills Kit SDK for Python.
# Please visit https://alexa.design/cookbook for additional examples on implementing slots, dialog management,
# session persistence, api calls, and more.
# This sample is built using the handler classes approach in skill builder.
import logging
import gettext
from urllib import response
import requests
from bs4 import BeautifulSoup
import datetime
from ask_sdk_core.skill_builder import SkillBuilder
from ask_sdk_core.dispatch_components import (
    AbstractRequestHandler, AbstractRequestInterceptor, AbstractExceptionHandler)
import ask_sdk_core.utils as ask_utils
from ask_sdk_core.handler_input import HandlerInput

from ask_sdk_model import Response
from alexa import data

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class handleData:
    def get_cardapio(self, date):
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
    def extract_menu(self,response):
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
        
        return self.filter_menu(dict_menu)

    @staticmethod
    def _normalize_parentheses(text):
        """Normaliza expressões de locais entre parênteses."""
        import re
        pattern = re.compile(r'\(([^)]*)\)')
        allowed = {"RS", "RA", "RU", "HC", "CAISM"}
        
        def repl(m):
            tokens = [t.strip() for t in m.group(1).split(',') if t.strip()]
            locs = [t for t in tokens if t in allowed]
            if not locs:
                return m.group(0)
            if len(locs) == 1:
                return f" no {locs[0]}. "
            if len(locs) == 2:
                return f" no {locs[0]} e no {locs[1]}. "
            return " " + ", ".join([f"no {loc}" for loc in locs[:-1]]) + f" e no {locs[-1]}. "
        
        return pattern.sub(repl, text)
    
    @staticmethod
    def _apply_phonemes(text):
        """Aplica phonemes SSML para pronúncia correta."""
        replacements = {
            'CAISM': '<phoneme alphabet="x-sampa" ph="ka\'i:zmi">CAISM</phoneme>',
            'RU': '<phoneme alphabet="x-sampa" ph="E.xi\'u">RU</phoneme>',
            'RS': '<phoneme alphabet="x-sampa" ph="E.xiE\'si">RS</phoneme>',
            'HC': '<phoneme alphabet="x-sampa" ph="a\'gase">HC</phoneme>',
            'RA': '<phoneme alphabet="x-sampa" ph="E.xi\'a">RA</phoneme>',
        }
        for key, value in replacements.items():
            text = text.replace(key, value)
        return text

    def filter_menu(self, extracted_menu):
        """Filtra e normaliza itens do menu."""
        exclude_terms = ['observações:', 'glúten', 'cardápio vegano será servido', 
                        'arroz e feijão', 'arroz integral e feijão', 'refresco']
        
        for key, value in extracted_menu.items():
            items_list = []
            for item in value:
                item = self._normalize_parentheses(item)
                items_list.extend(item.replace('\n', '#').split('#'))
            
            items_list = [x for x in items_list if x and 
                         not any(term in x.lower() for term in exclude_terms)]
            items_list = [self._apply_phonemes(self._normalize_parentheses(x)) for x in items_list]
            extracted_menu[key] = items_list
        
        return extracted_menu

    def print_menu_phrase(self, extracted_menu, key):
        items = extracted_menu[key]
        refeicao = items[0]
        prato_principal = items[1]
        acompanhamentos = items[2]
        salada = items[3]
        sobremesa = items[4]
        contem_lactose = items[5]

        # Monta a frase
        frase = (
            "<speak>"
            "<amazon:domain name=\"conversational\">"
            f"No {refeicao}, o prato principal é {prato_principal}, "
            f"acompanhado de {acompanhamentos}, "
            f"{salada}, "
            f"e de sobremesa tem {sobremesa}. "
            f"{contem_lactose} "
            "</amazon:domain>"
            "</speak>"
        )
        print(frase)
        return frase
# Usuário abre a skill: Aléxa, Abrir o cardápio do bandeco -> Usado para usuários que não sabem usar a skill
class LaunchRequestHandler(AbstractRequestHandler):
    """Handler for Skill Launch."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool

        return ask_utils.is_request_type("LaunchRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        _ = handler_input.attributes_manager.request_attributes["_"]
        speak_output = _(data.WELCOME_MESSAGE)

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )


# Handler genérico para cardápios - consolida 12 handlers em 1
class CardapioGenericoIntentHandler(AbstractRequestHandler):
    """Handler genérico para todas as intents de cardápio."""
    
    INTENT_MAP = {
        'AlmocoIntent': {'dias': 0, 'refeicoes': ['Almoco']},
        'JantarIntent': {'dias': 0, 'refeicoes': ['Jantar']},
        'CardapioIntent': {'dias': 0, 'refeicoes': ['Almoco', 'Jantar']},
        'AlmocoAmanhaIntent': {'dias': 1, 'refeicoes': ['Almoco']},
        'JantarAmanhaIntent': {'dias': 1, 'refeicoes': ['Jantar']},
        'CardapioAmanhaIntent': {'dias': 1, 'refeicoes': ['Almoco', 'Jantar']},
        'AlmocoVeganoIntent': {'dias': 0, 'refeicoes': ['Almoco_veg']},
        'JantarVeganoIntent': {'dias': 0, 'refeicoes': ['Jantar_veg']},
        'CardapioVeganoIntent': {'dias': 0, 'refeicoes': ['Almoco_veg', 'Jantar_veg']},
        'AlmocoAmanhaVeganoIntent': {'dias': 1, 'refeicoes': ['Almoco_veg']},
        'JantarAmanhaVeganoIntent': {'dias': 1, 'refeicoes': ['Jantar_veg']},
        'CardapioAmanhaVeganoIntent': {'dias': 1, 'refeicoes': ['Almoco_veg', 'Jantar_veg']},
    }

    def can_handle(self, handler_input):
        intent_name = ask_utils.get_intent_name(handler_input)
        return intent_name in self.INTENT_MAP

    def handle(self, handler_input):
        intent_name = ask_utils.get_intent_name(handler_input)
        config = self.INTENT_MAP[intent_name]
        
        handler = handleData()
        data_busca = datetime.datetime.now() + datetime.timedelta(days=config['dias'])
        html = handler.get_cardapio(data_busca)
        extracted_menu = handler.extract_menu(html)
        
        speak_output = ''.join(
            handler.print_menu_phrase(extracted_menu, refeicao) 
            for refeicao in config['refeicoes']
        )
        
        return handler_input.response_builder.speak(speak_output).response


class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("JantarIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        handler = handleData()
        html = handler.get_cardapio(datetime.datetime.now())
        extracted_menu = handler.extract_menu(html)
        speak_output = handler.print_menu_phrase(extracted_menu, 'Jantar')
        return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )



class HelpIntentHandler(AbstractRequestHandler):
    """Handler for Help Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.HelpIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        _ = handler_input.attributes_manager.request_attributes["_"]
        speak_output = _(data.HELP_MSG)

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )


class CancelOrStopIntentHandler(AbstractRequestHandler):
    """Single handler for Cancel and Stop Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return (ask_utils.is_intent_name("AMAZON.CancelIntent")(handler_input) or
                ask_utils.is_intent_name("AMAZON.StopIntent")(handler_input))

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        _ = handler_input.attributes_manager.request_attributes["_"]
        speak_output = _(data.GOODBYE_MSG)

        return (
            handler_input.response_builder
            .speak(speak_output)
            .response
        )

class FallbackIntentHandler(AbstractRequestHandler):
    """Single handler for Fallback Intent."""
    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AMAZON.FallbackIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        logger.info("In FallbackIntentHandler")
        speech = "Hmm, I'm not sure. You can say Hello or Help. What would you like to do?"
        reprompt = "I didn't catch that. What can I help you with?"

        return handler_input.response_builder.speak(speech).ask(reprompt).response

class SessionEndedRequestHandler(AbstractRequestHandler):
    """Handler for Session End."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("SessionEndedRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response

        # Any cleanup logic goes here.

        return handler_input.response_builder.response


class IntentReflectorHandler(AbstractRequestHandler):
    """The intent reflector is used for interaction model testing and debugging.
    It will simply repeat the intent the user said. You can create custom handlers
    for your intents by defining them above, then also adding them to the request
    handler chain below.
    """

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_request_type("IntentRequest")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        _ = handler_input.attributes_manager.request_attributes["_"]
        intent_name = ask_utils.get_intent_name(handler_input)
        speak_output = _(data.REFLECTOR_MSG).format(intent_name)

        return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )


class CatchAllExceptionHandler(AbstractExceptionHandler):
    """Generic error handling to capture any syntax or routing errors. If you receive an error
    stating the request handler chain is not found, you have not implemented a handler for
    the intent being invoked or included it in the skill builder below.
    """

    def can_handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> bool
        return True

    def handle(self, handler_input, exception):
        # type: (HandlerInput, Exception) -> Response
        logger.error(exception, exc_info=True)
        _ = handler_input.attributes_manager.request_attributes["_"]
        speak_output = _(data.ERROR)

        return (
            handler_input.response_builder
            .speak(speak_output)
            .ask(speak_output)
            .response
        )


class LocalizationInterceptor(AbstractRequestInterceptor):
    """
    Add function to request attributes, that can load locale specific data
    """

    def process(self, handler_input):
        locale = handler_input.request_envelope.request.locale
        i18n = gettext.translation(
            'data', localedir='locales', languages=[locale], fallback=True)
        handler_input.attributes_manager.request_attributes["_"] = i18n.gettext

# The SkillBuilder object acts as the entry point for your skill, routing all request and response
# payloads to the handlers above. Make sure any new handlers or interceptors you've
# defined are included below. The order matters - they're processed top to bottom.


sb = SkillBuilder()

sb.add_request_handler(LaunchRequestHandler())
sb.add_request_handler(CardapioGenericoIntentHandler())  # Substitui 12 handlers
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
sb.add_request_handler(IntentReflectorHandler())  # Mantém por último

sb.add_global_request_interceptor(LocalizationInterceptor())
sb.add_exception_handler(CatchAllExceptionHandler())

handler = sb.lambda_handler()
