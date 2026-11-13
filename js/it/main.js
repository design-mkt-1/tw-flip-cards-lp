import {TEMP_CONFIG} from "./enums/enums.js";
import {API_HEADERS} from "./enums/api.js";

import {addParamsToUrl, getQueryParams, getURLParams,} from "./utils/url.js";
import {injectAnalytics} from "./analytics.js";
import {executeRecaptcha} from "./api/resilve-recaptcha.js";
import {validateRegisterForm} from "./utils/form-validations.js";
import {LANG_TEXTS} from "./enums/form-text.js";

const locationOrigin = window.location.origin;
const isDevelopment =
    locationOrigin.includes("https://land-crm") ||
    window.location.hostname === "localhost" ||
    window.location.hostname === "127.0.0.1";

if (isDevelopment) {
    setTimeout(() => landingMainJsCode(), 1000);
} else {
    landingMainJsCode();
}

async function landingMainJsCode() {
    const langItems = document.querySelectorAll(".lang-list button");

    const formRegister = document.querySelector(".form-register")
    const regEmailInput = document.querySelector(".input-email");
    const regPasswordInput = document.querySelector(".input-password");
    const termsBlock = document.querySelector(".terms-wrap");
    const submitBtn = document.querySelector(".form-register-submit");

    const showPasswordBtn = document.querySelector(".show-password-btn");

    const siteRules = document.querySelector(".terms-link");
    const sitePolicy = document.querySelector(".policy-link");
    const siteLogin = document.querySelector(".login-text a");

    const modalWrapError = document.querySelector(".modal__wrap");
    const successModal = document.querySelector(".success-modal");
    const successModalBtn = document.querySelector(".success-modal__btn");

    const errorEmail = document.querySelector(".error-email span");
    const errorPassword = document.querySelector(".error-password span");
    const errorTerms = document.querySelector(".error-terms span");

    const ssoForm = document.querySelector("#sso");
    const ssoFormTmpToken = document.querySelector("#sso-tmpToken");
    const ssoFormRedirect = document.querySelector("#sso-redirect");

    const registerFormState = {
        loading: false,
        landing_id: null,
        _activeLang: langItems[0]?.textContent || "",
        email: "",
        password: "",
        terms: true,
        domain: null,
        ipAddress: ""
    };

    langItems.forEach((element) => {
        element.addEventListener("click", () => (registerFormState._activeLang = element.textContent))
    });

    // ---------------------------------------------

    showPasswordBtn.addEventListener('click', () => {
        regPasswordInput.type = regPasswordInput.type === 'password' ? 'text' : 'password';
    })

    // ---------------------------------------------

    if (isDevelopment) {
        initData(TEMP_CONFIG);
    } else {
        try {
            fetch("config.json")
                .then((res) => res.json())
                .then((data) => initData(data))
                .catch((err) => console.error("Error to get config", err));
        } catch (error) {
            console.error("Error in main fetch block:", error);
        }
    }

    function initData(data) {
        registerFormState.landing_id = data.id;
        registerFormState.email_registration = data.email_registration || null;
        try {
            fetch(data.landing, {
                method: "GET",
                headers: API_HEADERS,
            })
                .then((res) => res.json())
                .then((resData) => {
                    const {data} = resData;

                    injectAnalytics(data, isDevelopment);

                    if (!data.active) {
                        console.log({status: "landing is not active"});
                        const modalLandActive = document.querySelector(".disabled-modal");
                        modalLandActive?.classList.add("active");

                        setTimeout(() => {
                            const mailLink = document.querySelector(".mail-link");
                            mailLink.href = "mailto:support@top-win.com";
                            mailLink.textContent = "support@top-win.com";
                        }, 50);

                        return;
                    }
                    console.log({status: "landing is active"});

                    registerFormState.ladingData = data

                    registerFormState.recaptcha_key = data.recaptcha_key;

                    const recaptchaScript = document.createElement("script");
                    recaptchaScript.src =
                        "https://www.google.com/recaptcha/api.js?render=" +
                        registerFormState.recaptcha_key;
                    document.body.appendChild(recaptchaScript);

                    registerFormState.country = data.country
                    registerFormState.currency = data.currency

                    const landParams = getQueryParams();

                    siteRules.href = data.rules
                        ? addParamsToUrl(data.rules, landParams)
                        : addParamsToUrl(siteRules.href, landParams);
                    sitePolicy.href = data.policy
                        ? addParamsToUrl(data.policy, landParams)
                        : addParamsToUrl(sitePolicy.href, landParams);
                    siteLogin.href = data.login
                        ? addParamsToUrl(data.login, landParams)
                        : addParamsToUrl(siteLogin.href, landParams);
                })
                .catch((err) => console.error("Error to get landing data", err));
        } catch (error) {
            console.error("Error in nested fetch:", error);
        }
    }

    fetch("https://api.ipify.org?format=json")
        .then((response) => response.json())
        .then((data) => {
            registerFormState.ipAddress = data.ip;
            console.log({ip: data.ip})
        })
        .catch((error) => {
            console.error("Ошибка при получении IP-адреса пользователя:", error);
        });

    regEmailInput.addEventListener("input", () => {
        errorEmail.parentElement.classList.remove("active");
        registerFormState.email = regEmailInput.value || "";
        regEmailInput.closest(".input-wrap")?.classList.toggle(
            "valid",
            /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(registerFormState.email)
        );
    });
    regPasswordInput.addEventListener("input", () => {
        errorPassword.parentElement.classList.remove("active");
        registerFormState.password = regPasswordInput.value || "";
        regPasswordInput.closest(".input-password-wrap")?.classList.toggle(
            "valid",
            registerFormState.password.length >= 8
        );
    });
    termsBlock.addEventListener("click", () => {
        errorTerms.parentElement.classList.remove("active");
        registerFormState.terms = !registerFormState.terms;
        termsBlock.classList.toggle("active");
    });

    formRegister.addEventListener("submit", (event) => {
        event.preventDefault();


        const {
            email,
            password,
            promocode,
            landing_id,
            ladingData,
        } = registerFormState;

        const params = getURLParams()

        const data = {
            email,
            password,
            landing_id,
            language: (registerFormState._activeLang || 'en').toLowerCase(),
            currency: registerFormState.ladingData.currency || null,
            country: registerFormState.ladingData.country || null,
            promocode: registerFormState.ladingData.promocode || null,
            receivePromos: true,
            clientIp: registerFormState.ipAddress,
            ...params
        };

        // ...getURLParams()

        const isValid = validateRegisterForm({
            formState: registerFormState,
            errorEmail,
            errorPassword,
            errorTerms,
            activeLang: registerFormState._activeLang
        })

        if (isValid) {
            executeRecaptcha({
                recaptchaKey: registerFormState.recaptcha_key,
                data,
                onSuccess: () => {
                    register()
                },
                onError: () => modalWrapError.classList.add("active")
            })
        }

        function register() {
            try {
                submitBtn.disabled = true;
                submitBtn.textContent = LANG_TEXTS[registerFormState._activeLang || 'en'].submitBtnLoading;

                fetch(registerFormState.email_registration, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                    },
                    body: JSON.stringify(data),
                })
                    .then(async (res) => {
                        if (!res.ok) {
                            const dataError = await res.json();
                            throw new Error(dataError.errors[0]);
                        }

                        return res.json();
                    })
                    .then((response) => {
                        const {accessToken, redirectUrl} = response.data;

                        const landParams = getQueryParams();

                        /* The SSO hand-off must target the platform origin, not the
                           host inside `rules`. `rules` is the "Terms of use" link and
                           may point at a redirect proxy (twredirect.com), which the
                           platform answers with a 303 to an internal pod. The backend
                           already resolves the real platform origin while following
                           the affiliate click and appends the landing's redirect_link,
                           so `data.redirectUrl` is the authoritative target:
                           https://easy-topwin.icu/deposit */
                        const ssoTarget = resolveSsoTarget(redirectUrl, accessToken);

                        if (ssoTarget) {
                            ssoForm.action = `${ssoTarget.origin}/api/welcome`;
                            ssoFormTmpToken.value = accessToken;
                            ssoFormRedirect.value = addParamsToUrl(ssoTarget.redirect, landParams) || "/";
                            successModal?.classList.add("active");
                        } else {
                            /* No redirectUrl (landing without a partner_link, or a
                               platform response we could not resolve). Fall back to
                               the old rules-derived domain so the visitor can still
                               be handed off instead of being stuck on the modal. */
                            const fallback = resolveLegacySsoTarget(registerFormState.ladingData, registerFormState._activeLang);

                            if (fallback) {
                                ssoForm.action = `${fallback.origin}/api/welcome`;
                                ssoFormTmpToken.value = accessToken;
                                ssoFormRedirect.value = addParamsToUrl(fallback.redirect, landParams) || "/";
                                successModal?.classList.add("active");
                            } else {
                                console.error("Registration succeeded but no SSO target is available");
                            }
                        }
                    })
                    .catch((err) => {
                        console.log("Произошла ошибка при отправке формы", err);

                        let errorText = ""

                        errorEmail.parentElement.classList.add("active");

                        if (err.message === "reCAPTCHA verification failed. Please try again.") {
                            modalWrapError.classList.add("active");
                            errorText = "reCAPTCHA verification failed."
                        } else if (err.message === "Email already registered. Please use a different email or login.") {
                            // errorText =
                        }

                        errorEmail.textContent = errorText || `${err.message}`
                    })
                    .finally(() => {
                        submitBtn.disabled = false;
                        submitBtn.textContent = LANG_TEXTS[registerFormState._activeLang || 'en'].submitBtn;
                    });
            } catch (error) {
                console.error("Error in register function:", error);
                formSubmitBtn.disabled = false;
            }
        }
    });

    successModalBtn?.addEventListener("click", () => {
        ssoForm.submit();
    });
}

/**
 * Splits the backend-provided `redirectUrl` into the platform origin (the SSO
 * form target, `<origin>/api/welcome`) and the post-login redirect path.
 *
 * @param {string|undefined|null} redirectUrl
 * @param {string|undefined|null} accessToken
 * @returns {{origin: string, redirect: string}|null}
 */
function resolveSsoTarget(redirectUrl, accessToken) {
    if (!accessToken || !redirectUrl) return null;

    try {
        const url = new URL(redirectUrl, window.location.origin);

        return {
            origin: url.origin,
            redirect: url.origin + url.pathname + url.search,
        };
    } catch (error) {
        console.error("Invalid redirectUrl from backend", redirectUrl, error);

        return null;
    }
}

/**
 * Pre-fix behaviour, kept only as a safety net: the platform origin is taken
 * from `rules` and the path is `/{lang}/{redirect_link}`.
 *
 * @param {Object|null} landing
 * @param {string|null} activeLang
 * @returns {{origin: string, redirect: string}|null}
 */
function resolveLegacySsoTarget(landing, activeLang) {
    if (!landing || !landing.rules) return null;

    try {
        const origin = "https://" + new URL(landing.rules).hostname;
        const lang = (activeLang || "en").toLowerCase();
        const path = [lang, String(landing.redirect_link || "").replace(/^\/+/, "")]
            .filter(Boolean)
            .join("/");

        return {origin, redirect: origin + "/" + path};
    } catch (error) {
        console.error("Could not derive a legacy SSO target", landing && landing.rules, error);

        return null;
    }
}
