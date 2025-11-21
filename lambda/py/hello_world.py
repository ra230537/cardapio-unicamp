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
    def __init__(self):
        pass
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

    def filter_menu(self, extracted_menu):
        import re
        def _normalize_parentheses(text: str) -> str:
            pattern = re.compile(r'\(([^)]*)\)')
            allowed = {"RS", "RA", "RU", "HC", "CAISM"}
            def repl(m):
                raw = m.group(1)
                tokens = [t.strip() for t in raw.split(',') if t.strip()]
                locs = [t for t in tokens if t in allowed]
                if not locs:
                    return m.group(0)
                if len(locs) == 1:
                    return f" no {locs[0]}. "
                if len(locs) == 2:
                    return f" no {locs[0]} e no {locs[1]}. "
                return " " + ", ".join([f"no {loc}" for loc in locs[:-1]]) + f" e no {locs[-1]}. "
            return pattern.sub(repl, text)
        for key, value in extracted_menu.items():
            items_list = []
            for item in value:
                # Normaliza grupos entre parênteses antes de quebrar por linhas
                item = _normalize_parentheses(item)
                splitted_item = item.replace('\n', '#').split('#')
                items_list.extend(splitted_item)
            items_list = [x for x in items_list if x]
            items_list = [x for x in items_list if 'Observações:'.upper() not in x.upper()]
            items_list = [x for x in items_list if 'Glúten'.upper() not in x.upper()]
            items_list = [x for x in items_list if 'cardápio vegano será servido'.upper() not in x.upper()]
            items_list = [x for x in items_list if 'ARROZ E FEIJÃO'.upper() not in x.upper()]
            items_list = [x for x in items_list if 'ARROZ INTEGRAL E FEIJÃO'.upper() not in x.upper()]
            items_list = [x for x in items_list if 'REFRESCO'.upper() not in x.upper()]
            # Reaplica normalização caso algum item tenha novos grupos
            items_list = [_normalize_parentheses(x) for x in items_list]
            items_list = [x.replace('CAISM', '<phoneme alphabet="x-sampa" ph="ka\'i:zmi">CAISM</phoneme>') for x in items_list]
            items_list = [x.replace('RU', '<phoneme alphabet="x-sampa" ph="E.xi\'u">RU</phoneme>') for x in items_list]
            items_list = [x.replace('RS', '<phoneme alphabet="x-sampa" ph="E.xiE\'si">RS</phoneme>') for x in items_list]
            items_list = [x.replace('HC', '<phoneme alphabet="x-sampa" ph="a\'gase">HC</phoneme>') for x in items_list]
            items_list = [x.replace('RA', '<phoneme alphabet="x-sampa" ph="E.xi\'a">RA</phoneme>') for x in items_list]
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


# Usado para usuário que sabe usar a skill
class HelloWorldIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("HelloWorldIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        _ = handler_input.attributes_manager.request_attributes["_"]
        speak_output = _(data.HELLO_MSG)

        return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )

# Usado para usuário que sabe usar a skill
class AlmocoIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AlmocoIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        handler = handleData()
        html = handler.get_cardapio(datetime.datetime.now())
        extracted_menu = handler.extract_menu(html)
        speak_output = handler.print_menu_phrase(extracted_menu, 'Almoco')
        return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )

class JantarIntentHandler(AbstractRequestHandler):
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

class CardapioIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("CardapioIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        handler = handleData()
        html = handler.get_cardapio(datetime.datetime.now())
        extracted_menu = handler.extract_menu(html)
        speak_output = handler.print_menu_phrase(extracted_menu, 'Almoco')
        speak_output += handler.print_menu_phrase(extracted_menu, 'Jantar')
        return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )


class AlmocoAmanhaIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AlmocoAmanhaIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        handler = handleData()
        html = handler.get_cardapio(datetime.datetime.now()+datetime.timedelta(days=1))
        extracted_menu = handler.extract_menu(html)
        speak_output = handler.print_menu_phrase(extracted_menu, 'Almoco')
        return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )

class JantarAmanhaIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("JantarAmanhaIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        handler = handleData()
        html = handler.get_cardapio(datetime.datetime.now()+datetime.timedelta(days=1))
        extracted_menu = handler.extract_menu(html)
        speak_output = handler.print_menu_phrase(extracted_menu, 'Jantar')
        return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )

class CardapioAmanhaIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("CardapioAmanhaIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        handler = handleData()
        html = handler.get_cardapio(datetime.datetime.now()+datetime.timedelta(days=1))
        extracted_menu = handler.extract_menu(html)
        speak_output = handler.print_menu_phrase(extracted_menu, 'Almoco')
        speak_output += handler.print_menu_phrase(extracted_menu, 'Jantar')
        return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )

##### Vegano #####

class AlmocoVeganoIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AlmocoVeganoIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        handler = handleData()
        html = handler.get_cardapio(datetime.datetime.now())
        extracted_menu = handler.extract_menu(html)
        speak_output = handler.print_menu_phrase(extracted_menu, 'Almoco_veg')
        return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )

class JantarVeganoIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("JantarVeganoIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        handler = handleData()
        html = handler.get_cardapio(datetime.datetime.now())
        extracted_menu = handler.extract_menu(html)
        speak_output = handler.print_menu_phrase(extracted_menu, 'Jantar_veg')
        return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )

class CardapioVeganoIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("CardapioVeganoIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        handler = handleData()
        html = handler.get_cardapio(datetime.datetime.now())
        extracted_menu = handler.extract_menu(html)
        speak_output = handler.print_menu_phrase(extracted_menu, 'Almoco_veg')
        speak_output += handler.print_menu_phrase(extracted_menu, 'Jantar_veg')
        return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )

class AlmocoAmanhaVeganoIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("AlmocoAmanhaVeganoIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        handler = handleData()
        html = handler.get_cardapio(datetime.datetime.now()+datetime.timedelta(days=1))
        extracted_menu = handler.extract_menu(html)
        speak_output = handler.print_menu_phrase(extracted_menu, 'Almoco_veg')
        return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )

class JantarAmanhaVeganoIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("JantarAmanhaVeganoIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        handler = handleData()
        html = handler.get_cardapio(datetime.datetime.now()+datetime.timedelta(days=1))
        extracted_menu = handler.extract_menu(html)
        speak_output = handler.print_menu_phrase(extracted_menu, 'Jantar_veg')
        return (
            handler_input.response_builder
            .speak(speak_output)
            # .ask("add a reprompt if you want to keep the session open for the user to respond")
            .response
        )

class CardapioAmanhaVeganoIntentHandler(AbstractRequestHandler):
    """Handler for Hello World Intent."""

    def can_handle(self, handler_input):
        # type: (HandlerInput) -> bool
        return ask_utils.is_intent_name("CardapioAmanhaVeganoIntent")(handler_input)

    def handle(self, handler_input):
        # type: (HandlerInput) -> Response
        handler = handleData()
        html = handler.get_cardapio(datetime.datetime.now()+datetime.timedelta(days=1))
        extracted_menu = handler.extract_menu(html)
        speak_output = handler.print_menu_phrase(extracted_menu, 'Almoco_veg')
        speak_output += handler.print_menu_phrase(extracted_menu, 'Jantar_veg')
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
sb.add_request_handler(HelloWorldIntentHandler())
sb.add_request_handler(AlmocoIntentHandler())
sb.add_request_handler(JantarIntentHandler())
sb.add_request_handler(CardapioIntentHandler())
sb.add_request_handler(AlmocoAmanhaIntentHandler())
sb.add_request_handler(JantarAmanhaIntentHandler())
sb.add_request_handler(CardapioAmanhaIntentHandler())
sb.add_request_handler(AlmocoVeganoIntentHandler())
sb.add_request_handler(JantarVeganoIntentHandler())
sb.add_request_handler(CardapioVeganoIntentHandler())
sb.add_request_handler(AlmocoAmanhaVeganoIntentHandler())
sb.add_request_handler(JantarAmanhaVeganoIntentHandler())
sb.add_request_handler(CardapioAmanhaVeganoIntentHandler())
sb.add_request_handler(HelpIntentHandler())
sb.add_request_handler(CancelOrStopIntentHandler())
sb.add_request_handler(FallbackIntentHandler())
sb.add_request_handler(SessionEndedRequestHandler())
# make sure IntentReflectorHandler is last so it doesn't override your custom intent handlers
sb.add_request_handler(IntentReflectorHandler())

sb.add_global_request_interceptor(LocalizationInterceptor())

sb.add_exception_handler(CatchAllExceptionHandler())

handler = sb.lambda_handler()
