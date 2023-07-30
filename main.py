import vkinderBot
import config

if __name__ == '__main__':
    vkinderBot = vkinderBot.VkinderBot(config.user_token, config.login, config.passw, config.group_token, config.pg_link)
    vkinderBot.start()
