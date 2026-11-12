/**
 * @returns {string}
 * @description Функция для получения параметров текущего URL
 */
export const getQueryParams = () => {
    return window.location.search ? window.location.search.substring(1) : '';
}

/**
 * @param url {string}
 * @param params {string}
 * @description Если нет параметров, возвращаем URL как есть
 * @returns {string}
 */
export const addParamsToUrl = (url, params) => {
    if (!params) return url;
    return url.includes("?") ? `${url}&${params}` : `${url}?${params}`;
}

/**
 * @returns {string|null}
 */
export const getPromocodeFromURL = () => {
    const urlParams = new URLSearchParams(window.location.search);
    const promocode = urlParams.get('promocode');

    if (promocode) {
        return promocode;
    } else {
        return null;
    }
}

/**
 * @returns {{}|null}
 */
export const getURLParams = () => {
    const urlObject = new URL(window.location.href);
    const params = {};
    const searchParams = urlObject.searchParams;

    if (searchParams.toString() === '') {
        return null;
    }
    for (const [key, value] of searchParams.entries()) {
        params[key] = value;
    }

    return params;
}