import {LANG_TEXTS} from "../enums/form-text.js";

/**
 * @param {Object} formState
 * @param {HTMLDivElement} errorEmail
 * @param {HTMLDivElement} errorPassword
 * @param {HTMLDivElement} errorTerms
 * @param {string} activeLang
 * @returns {boolean}
 */
export const validateRegisterForm = ({formState, errorEmail, errorPassword, errorTerms, activeLang}) => {
    let _isValid = true

    if (!formState.email) {
        _isValid = false
        errorEmail.parentElement.classList.add("active")
        errorEmail.textContent = LANG_TEXTS[activeLang]["requiredField"]
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(formState.email)) {
        errorEmail.parentElement.classList.add("active")
        errorEmail.textContent = LANG_TEXTS[activeLang]["mailExample"]

        console.log(formState.email)

        _isValid = false
    }

    if (!formState.password) {
        _isValid = false
        errorPassword.parentElement.classList.add("active")
        errorPassword.textContent = LANG_TEXTS[activeLang]["requiredField"]
    } else if (formState.password.length < 8) {
        _isValid = false
        errorPassword.parentElement.classList.add("active")
        errorPassword.textContent = LANG_TEXTS[activeLang]["passwordMinLength"]
    }

    if (!formState.terms) {
        _isValid = false
        errorTerms.parentElement.classList.add("active")
        errorTerms.textContent = LANG_TEXTS[activeLang]["termsConfirm"]
    }

     return _isValid
}