/* Top Win shell copy — every word the header, the footer and the registration
   dialog say, in every language the template ships.

   SHARED FILE. A campaign never edits this; tools/drift.py fails CI if it
   moves. Campaign copy — the headline, the mechanic's labels, anything the
   page says that is not chrome — lives in `strings` inside campaign.js and is
   merged over this table at boot, campaign winning on collision.

   ── Adding a language ────────────────────────────────────────
   Two object literals and one array entry, and nothing else:

     1. add `pl: { … }` to LOCALES below, with its BCP-47 tag, its endonym and
        its flag file
     2. add `pl: { … }` to TW_STRINGS below — the ~50 keys in this file
     3. add `pl: { … }` to `strings` in campaign.js — the handful of keys that
        campaign owns
     4. add 'pl' to `languages` in campaign.js

   No new file, no new <script> tag, no HTML edit, no CSS edit, no component
   edit. Translating this file once means every future campaign inherits the
   language for free, because the template is copied down into each clone.

   ── Why `ua` and not `uk` ────────────────────────────────────
   `ua` is a region subtag, not a language; the language is `uk`. The design
   and the menu say UA, so `ua` is kept as the internal code and LOCALES.tag
   carries the real one for anywhere a browser is listening —
   document.documentElement.lang and the form payload. Without that map every
   Ukrainian browser (navigator.language === 'uk-UA') misses the table and
   lands on the fallback, and only *looks* right because the fallback happens
   to be Ukrainian.

   ── Interpolation ────────────────────────────────────────────
   `{name}` in a string is replaced by t()'s second argument. The shell fills
   {percent} {amount} {currency} {spins} from campaign.js `offer` — so the
   offer figures are written ONCE, as numbers, and each locale writes only the
   sentence shape around them. Changing 225% / 15000 to 300% / 20000 is a
   two-value edit in campaign.js and no language table is touched.

   ── \n means a real <br> ─────────────────────────────────────
   The markup carries none. js/i18n.js splits on it.

   ── Sentences with links are split ───────────────────────────
   agree.pre / agree.terms / agree.mid / agree.privacy / agree.post are five
   nodes, not one string with a tag in it, so a locale can reorder the words
   around the two anchors. Never put markup in a string here. */

var TW_STRINGS = (function () {
  'use strict';

  return {

    /* The default, the fallback, and the only table read straight off the
       design. Everything here was transcribed from the Figma nodes rather
       than translated -- these are the words the client signed off,
       apostrophes and casing included. */
    ua: {
      'hdr.sound':          'Увімкнути або вимкнути звук',
      'hdr.lang':           'Мова',

      'promo.title':        'Вітальний спортивний бонус',
      'promo.pct':          '{percent}',
      'promo.amount':       'до {amount} {currency}',
      'promo.spins':        '+ {spins} FS',

      'tabs.label':         'Спосіб реєстрації',
      'tab.phone':          'ТЕЛЕФОН',
      'tab.email':          'EMAIL',

      /* The placeholders are the design's own. The email field has no label
         above it, which is why the word sits inside the box; the phone field
         shows the shape of the number behind the fixed dial code. */
      'field.email':        'Email',
      'field.phone':        '00 000 0000',
      'field.phoneLabel':   'Номер телефону',
      'field.password':     'Пароль',
      'field.passwordHint': 'Введіть пароль',
      'field.reveal':       'Показати пароль',
      'field.hide':         'Сховати пароль',

      'err.phone':          'Невірний номер телефону',
      'err.email':          'Невірна адреса електронної пошти',
      'err.password':       'Пароль занадто короткий',
      'err.network':        'Не вдалося надіслати. Спробуйте ще раз',

      'agree.aria':         'Мені 18 років, і я приймаю умови',
      'agree.pre':          'Мені 18 років, і я приймаю ',
      'agree.terms':        'Умови Використання',
      'agree.mid':          ' та ',
      'agree.privacy':      'Політику конфіденційності',
      'agree.post':         '.',

      'cta.register':       'ЗАРЕЄСТРУВАТИСЬ',
      'foot.have':          'Вже є акаунт?',
      'foot.login':         'Увійти',

      'dialog.close':       'Закрити',
      'done.title':         'Реєстрація успішна!',
      'done.login':         'Логін:',
      'done.password':      'Пароль:',
      'done.copy':          'Копіювати',
      'done.copied':        'Скопійовано',
      'done.note':          'Збережіть ваші дані для входу',
      'cta.website':        'ПЕРЕЙТИ НА САЙТ',

      /* The year is the design's, not the clock's: it is copy the client set,
         so it changes when they change it, not on 1 January. */
      'footer.pay':         'Способи оплати',
      'footer.copy':        '© 2026 Усі права захищені'
    },

    /* Written, not transcribed. The Figma page carries the dialog in
       Ukrainian only -- fourteen variants, all UA -- so this table has never
       been read by the designer or by a native speaker. Flag it to the client
       before a campaign runs Russian traffic. */
    ru: {
      'hdr.sound':          'Включить или выключить звук',
      'hdr.lang':           'Язык',

      'promo.title':        'Приветственный спортивный бонус',
      'promo.pct':          '{percent}',
      'promo.amount':       'до {amount} {currency}',
      'promo.spins':        '+ {spins} FS',

      'tabs.label':         'Способ регистрации',
      'tab.phone':          'ТЕЛЕФОН',
      'tab.email':          'EMAIL',

      'field.email':        'Email',
      'field.phone':        '00 000 0000',
      'field.phoneLabel':   'Номер телефона',
      'field.password':     'Пароль',
      'field.passwordHint': 'Введите пароль',
      'field.reveal':       'Показать пароль',
      'field.hide':         'Скрыть пароль',

      'err.phone':          'Неверный номер телефона',
      'err.email':          'Неверный адрес почты',
      'err.password':       'Пароль слишком короткий',
      'err.network':        'Не удалось отправить. Попробуйте ещё раз',

      'agree.aria':         'Мне 18 лет, и я принимаю условия',
      'agree.pre':          'Мне 18 лет, и я принимаю ',
      'agree.terms':        'Условия использования',
      'agree.mid':          ' и ',
      'agree.privacy':      'Политику конфиденциальности',
      'agree.post':         '.',

      'cta.register':       'ЗАРЕГИСТРИРОВАТЬСЯ',
      'foot.have':          'Уже есть аккаунт?',
      'foot.login':         'Войти',

      'dialog.close':       'Закрыть',
      'done.title':         'Регистрация успешна!',
      'done.login':         'Логин:',
      'done.password':      'Пароль:',
      'done.copy':          'Копировать',
      'done.copied':        'Скопировано',
      'done.note':          'Сохраните свои данные для входа',
      'cta.website':        'ПЕРЕЙТИ НА САЙТ',

      'footer.pay':         'Способы оплаты',
      'footer.copy':        '© 2026 Все права защищены'
    },

    /* Also written rather than reviewed by a native speaker. Same caveat. */
    en: {
      'hdr.sound':          'Toggle sound',
      'hdr.lang':           'Language',

      'promo.title':        'Welcome sports bonus',
      'promo.pct':          '{percent}',
      'promo.amount':       'up to {amount} {currency}',
      'promo.spins':        '+ {spins} FS',

      'tabs.label':         'Sign up with',
      'tab.phone':          'PHONE',
      'tab.email':          'EMAIL',

      'field.email':        'Email',
      'field.phone':        '00 000 0000',
      'field.phoneLabel':   'Phone number',
      'field.password':     'Password',
      'field.passwordHint': 'Enter password',
      'field.reveal':       'Show password',
      'field.hide':         'Hide password',

      'err.phone':          'Invalid phone number',
      'err.email':          'Invalid email address',
      'err.password':       'Password is too short',
      'err.network':        'Could not send. Please try again',

      'agree.aria':         'I am 18 and I accept the terms',
      'agree.pre':          'I am 18 years old and I accept the ',
      'agree.terms':        'Terms of Use',
      'agree.mid':          ' and the ',
      'agree.privacy':      'Privacy Policy',
      'agree.post':         '.',

      'cta.register':       'REGISTER',
      'foot.have':          'Already have an account?',
      'foot.login':         'Log in',

      'dialog.close':       'Close',
      'done.title':         'Registration successful!',
      'done.login':         'Login:',
      'done.password':      'Password:',
      'done.copy':          'Copy',
      'done.copied':        'Copied',
      'done.note':          'Save your login details',
      'cta.website':        'GO TO WEBSITE',

      'footer.pay':         'Payment methods',
      'footer.copy':        '© 2026 All rights reserved'
    }
  };
}());

/* The language switcher's own data. `tag` is the BCP-47 tag the browser is
   told; `name` is the endonym, which is never translated -- a language names
   itself in its own words; `flag` is a file in assets/img/icons/, not an emoji,
   because Windows draws the flag emoji as the letters "UA".

   GB is the convention for English: English is not a country, so the flag is
   a convention and the endonym beside it is what actually settles it. */
var TW_LOCALES = {
  ua: { tag: 'uk', name: 'Українська', flag: 'flag-ua.svg' },
  ru: { tag: 'ru', name: 'Русский',    flag: 'flag-ru.svg' },
  en: { tag: 'en', name: 'English',    flag: 'flag-gb.svg' }
};
