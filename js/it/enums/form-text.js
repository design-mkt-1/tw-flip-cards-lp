// Dont edit structure and variable name LANG_TEXTS, edit only values
export const LANG_TEXTS = {"EN":{"login1":"Already have an account? ","login2":" Log in","terms1":"I am 18 years old and I accept the ","terms2":"Terms and Conditions ","terms3":"and ","terms4":"Privacy Policy ","submitBtn":"Continue","offerTitle":"Welcome bonus","successBtn":"Go to the site","mailExample":"Please enter a valid email address","successText":"Your registration is complete. Welcome to the winners' circle.","successTitle":"Congratulations!","termsConfirm":"Please confirm your agreement with the terms.","offerSubtitle":"225% to 15000 ₴","requiredField":"This field is required.","modalErrorText":"Unfortunately, we were unable to verify your identity. Please try registering using a different browser or device.","inputEmailLabel":"Email","submitBtnLoading":"Loading…","passwordMinLength":"Password must be at least 8 characters long.","inputPasswordLabel":"Password","inputEmailPlaceholder":"example@email.com","emailAlreadyRegistered":"Email is already registered.","inputPasswordPlaceholder":"Password"},"DE":{"login1":"Du hast bereits ein Konto? ","login2":" Anmelden","terms1":"Ich bin 18 Jahre alt und akzeptiere die ","terms2":"Allgemeinen Geschäftsbedingungen ","terms3":"und die ","terms4":"Datenschutzerklärung ","submitBtn":"Weiter","offerTitle":"Willkommensbonus","successBtn":"Zur Website","mailExample":"Bitte gib eine gültige E-Mail-Adresse ein","successText":"Deine Registrierung ist abgeschlossen. Willkommen im Kreis der Gewinner!","successTitle":"Herzlichen Glückwunsch!","termsConfirm":"Bitte bestätige, dass du den Bedingungen zustimmst.","offerSubtitle":"225 % bis zu 15.000 ₴","requiredField":"Dieses Feld ist erforderlich.","modalErrorText":"Leider konnten wir deine Identität nicht überprüfen. Bitte versuche, dich mit einem anderen Browser oder Gerät zu registrieren.","inputEmailLabel":"E-Mail-Adresse","submitBtnLoading":"Wird geladen …","passwordMinLength":"Das Passwort muss mindestens 8 Zeichen lang sein.","inputPasswordLabel":"Passwort","inputEmailPlaceholder":"beispiel@email.com","emailAlreadyRegistered":"Diese E-Mail-Adresse ist bereits registriert.","inputPasswordPlaceholder":"Passwort"}}

// TopWin, decision 25 (addendum 2026-11-12): the page has UA, RU and EN buttons, IT's
// sample has EN and DE. IT's own English text is used for all three; nothing is
// translated, EXCEPT the register button's two labels, which follow the page
// language. They are read at the moment IT's main.js sets them, from the landing's own
// strings (cta.register, cta.loading), so every landing shows its own text.
LANG_TEXTS.UA = {...LANG_TEXTS.EN};
LANG_TEXTS.RU = {...LANG_TEXTS.EN};
["UA", "RU", "EN"].forEach((code) => {
    const own = (key, fallback) => () => {
        const v = window.TW && window.TW.t ? window.TW.t(key) : key;
        return v && v !== key ? v : fallback;
    };
    Object.defineProperties(LANG_TEXTS[code], {
        submitBtn: {enumerable: true, get: own("cta.register", "Continue")},
        submitBtnLoading: {enumerable: true, get: own("cta.loading", "Loading…")},
    });
});
