/**
 * Выполняет reCAPTCHA и добавляет токен в объект данных, затем вызывает callback.
 *
 * @param {string} recaptchaKey - Ключ reCAPTCHA.
 * @param {Object} data - Объект, куда будет добавлен токен (`g-recaptcha-response`).
 * @param {Function} onSuccess - Функция, вызываемая после успешного получения токена.
 * @param {Function} [onError] - Функция, вызываемая при ошибке получения токена.
 */
export const executeRecaptcha = ({recaptchaKey, data, onSuccess, onError}) => {
    try {
        grecaptcha
            .execute(recaptchaKey, {action: "register"})
            .then(function (token) {
                if (token) {
                    data["g-recaptcha-response"] = token;
                    onSuccess();
                } else {
                    console.log("Failed to get reCAPTCHA token");
                    if (onError) onError();
                }
            })
            .catch(function (error) {
                console.error("reCAPTCHA error:", error);
                if (onError) onError();
            });
    } catch (error) {
        console.error("Error executing reCAPTCHA:", error);
        if (onError) onError();
    }
}