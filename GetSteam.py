import requests
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
import time
import pickle
import csv
import telebot
import os

bot = telebot.TeleBot('EnterYourBotKey')


url_float = 'https://api.csgofloat.com/?url='
url_login = 'https://steamcommunity.com/login/home/?goto='
already_buy_err = 'You cannot purchase this item because somebody else has already purchased it.'
mark_err = 'You must agree to the terms of the Steam Subscriber Agreement to complete this transaction.'

#Логин в стиме для работы
def LoginBrowser():
    is_login = False

    options = webdriver.ChromeOptions()
    #options.add_argument('headless')  # для открытия headless-браузера
    browser = webdriver.Chrome(executable_path='chromedriver.exe')
#Проверка наличия куки файлов
    try:
        cookies = pickle.load(open("cookies_steam.pkl", "rb"))
        print('Куки STEAM найдены загружаем')
        browser.get('https://steamcommunity.com')
        for cookie in cookies:
            browser.add_cookie(cookie)
        browser.get('https://steamcommunity.com')

        browser.find_element_by_id('account_pulldown')
        print('Куки STEAM загружены')
    except Exception:
        #Логин если куки отсутвуют или не работают
        browser.get(url_login)
        input('Ожидание входа в стим. Нажмите ENTER для продолжения.')
        pickle.dump(browser.get_cookies(), open("cookies_steam.pkl", "wb"))

    browser.get('https://steamcommunity.com')
    # Провека логина в аккаунт
    try:
        browser.find_element_by_id('account_pulldown')
        is_login = True
    except Exception:
        is_login = False

    if (is_login == False):
        print('Не удалось зайти в аккаунт')
        exit(4)
    return browser

#Функция проверки предмета
def CheckItem(browser, item):
    sum_err = 0;
    actions = ActionChains(browser)
    browser.get(item['skin_link'])
    ssa_check = False
    b = getBalance(browser)
    try:
        browser.find_element_by_class_name('my_market_header_active')
        skins = browser.find_elements_by_class_name('market_listing_row')
        skins.pop(0)
    except Exception:
        skins = browser.find_elements_by_class_name('market_listing_row')

    skins.pop(0)
    for skin in skins:
        id = skin.get_attribute('id')
        price = skin.find_element_by_class_name('market_listing_price_with_fee').text
        if skin.find_element_by_class_name('market_listing_price').text == 'Sold!':
            print('Уже продано скипаем')
            continue
        price = float(price.split()[0].replace(',','.'))
        print('Цена скина: ' + str(price))
        if(price > b):
            print("Дорогой предмет")
            break
        try:
            actions.move_to_element(skin.find_element_by_id(id + '_image'))
            skin.find_element_by_id(id + '_image').click()
            skin.find_element_by_id(id + '_actionmenu_button').click()
            link = browser.find_elements_by_class_name('popup_menu_item')[-1].get_attribute("href")
            r = requests.get(url_float + link).json()

        except Exception:
            sum_err += 1
            bot.send_message(352537788, 'Ошибка но мы прололжаем')
            if(sum_err > 6):
                bot.send_message(352537788, 'Много ошибок бот остановлен')
                exit(5)
            continue
        try:
            bot.send_message(352537788, r['error'] + 'Ждем ...')
            while True:
                time.sleep(300)
                r = requests.get(url_float + link).json()
                print(r['error'])
                bot.send_message(352537788, r['error'] + 'Ждем ...')
        except Exception:
            floatitem = float(r['iteminfo']['floatvalue'])
            print('Флоат скина: ' + str(floatitem))
            if (floatitem <= float(item['max_float'])):
                if(price < float(item['min_price_csmoney'])*0.86):

                    print('Ура пишем боту и покупаем Найден флота = ' + str(r['iteminfo']['floatvalue']))
                    isItemBought = BuyItem(skin, browser, ssa_check)
                    if(isItemBought == True):
                        BotItemFind(price, floatitem, item['skin_name'])
                        b = getBalance(browser)
                    else:
                        bot.send_message(352537788, "Найден предмет с флотом" +str(floatitem) +" но не смогли купить")
                    ssa_check = True

                else:
                    bot.send_message(352537788, "Найден предмет: " +item['skin_name'] +" с флотам: " +str(floatitem) +" , но дорогой за "+str(price))
                    BotItemErr('Для скриншота')

# Покупка подходящего предмета
def BuyItem(skin, browser, ssa_check):

    skin.find_element_by_class_name('market_listing_buy_button').click()
    if ssa_check == False:
        browser.find_element_by_id('market_buynow_dialog_accept_ssa').click()
    browser.find_element_by_id('market_buynow_dialog_purchase').click()
    i = 0
    while i < 10:
        try:
            time.sleep(3)
            browser.save_screenshot('screenie.png')
            browser.find_element_by_id('market_buynow_dialog_close').click()
            print('Покупка успешна продолжаем')
            return True
        except Exception:
            print('Не удалось купить. Попытка ' + str(i))

            if browser.find_element_by_id('market_buynow_dialog_error_text') == mark_err:
                print('Ошибка соглашения. Ещё раз')
                browser.save_screenshot('screenie_err.png')
                BotItemErr('Ошибка соглашения.')
                browser.find_element_by_id('market_buynow_dialog_accept_ssa').click()

            if browser.find_element_by_id('market_buynow_dialog_error_text') == already_buy_err:
                print('Ошибка уже куплено гг')
                browser.save_screenshot('screenie_err.png')
                BotItemErr('Ошибка куплено.')
                browser.find_element_by_id('market_buynow_dialog_cancel').click()
                return False
            time.sleep(3)
            browser.find_element_by_id('market_buynow_dialog_purchase').click()
            i += 1
    browser.save_screenshot('screenie_err.png')
    browser.find_element_by_id('market_buynow_dialog_cancel').click()
    return False

#Проверка баланса аккаунта, если низкий остановка работы
def getBalance(browser):
    balance = browser.find_element_by_id('marketWalletBalanceAmount').text
    balance = float(balance.split()[0].replace(',','.'))
    print('Баланс аккаунта: ' + str(balance))
    if balance < 50:
        print("Маленький баланс")
        bot.send_message(352537788, "Маленький баланс")
        os.system('shutdown -s')
        exit(3)
    return balance

def main():
    steam = LoginBrowser()
    c = 0
    while True:
        table = open('Путь до файла со списком предиетов')
        Items = csv.DictReader(table)
        for item in Items:
            print(item['skin_name'])
            CheckItem(steam, item)
        c += 1
        bot.send_message(352537788, 'Круг закончен номер ' + str(c))
        table.close()
        time.sleep(90)

#Логирование действия в бот телеграма
def BotItemFind(price, floatitem, name):
    photo = open('screenie.png', 'rb')
    bot.send_message(352537788, "Куплен предмет:"+ name + " за "+str(price) + " с флотом "+ str(floatitem)  +  " Скриншот:")
    bot.send_photo(352537788, photo)
    photo.close()

# Функция отладки для проверки ошибки
def BotItemErr(text):
    photo = open('screenie_err.png', 'rb')
    bot.send_message(352537788, text)
    bot.send_photo(352537788, photo)
    photo.close()


#Для автоматического перезапуска программы при ошибки из-за не известной ошибки
if __name__ == "__main__":
    err = 0
    while err < 5:
        try:
            main()
        except Exception:
            err += 1
            bot.send_message(352537788, 'Серъёзная ошибка, начинаем заново')
            time.sleep(60)

    bot.send_message(352537788, 'Много главных ошибок, программа остановленна')
