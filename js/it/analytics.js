export function injectAnalytics(data) {
    try {
        if (!data) {
            console.error('Ошибка: отсутствует тип аналитики или ID');
            return false;
        }

        if (data.analytics_google) {
            const googleScriptSrc = document.createElement('script');
            googleScriptSrc.async = true;
            googleScriptSrc.src = `https://www.googletagmanager.com/gtag/js?id=${data.analytics_google}`;

            const googleScriptInit = document.createElement('script');
            googleScriptInit.textContent = `
                window.dataLayer = window.dataLayer || [];
                function gtag(){dataLayer.push(arguments);}
                gtag('js', new Date());
                gtag('config', '${data.analytics_google}');
            `;

            document.head.appendChild(googleScriptSrc);
            document.head.appendChild(googleScriptInit);

            console.log(`Google Analytics (${data.analytics_google}) успешно добавлен`);
        }

        if (data.analytics_yandex) {
            const yandexScript = document.createElement('script');
            yandexScript.type = 'text/javascript';
            yandexScript.textContent = `
                (function(m,e,t,r,i,k,a){m[i]=m[i]||function(){(m[i].a=m[i].a||[]).push(arguments)};
                  m[i].l=1*new Date();
                  for (var j = 0; j < document.scripts.length; j++) {if (document.scripts[j].src === r) { return; }}
                  k=e.createElement(t),a=e.getElementsByTagName(t)[0],k.async=1,k.src=r,a.parentNode.insertBefore(k,a)})
                (window, document, "script", "https://mc.yandex.ru/metrika/tag.js", "ym");
                
                ym(${data.analytics_yandex}, "init", {
                  clickmap:true,
                  trackLinks:true,
                  accurateTrackBounce:true
                });
          `;

            const yandexNoscript = document.createElement('noscript');
            const yandexDiv = document.createElement('div');
            const yandexImg = document.createElement('img');
            yandexImg.src = `https://mc.yandex.ru/watch/${data.analytics_yandex}`;
            yandexImg.style = 'position:absolute; left:-9999px;';
            yandexImg.alt = '';

            yandexDiv.appendChild(yandexImg);
            yandexNoscript.appendChild(yandexDiv);

            document.head.appendChild(yandexScript);
            document.head.appendChild(yandexNoscript);

            console.log(`Yandex Metrika (${data.analytics_yandex}) успешно добавлен`);
        }
        if (data.gtm_tag) {
            // GTM Script (head)
            const gtmScript = document.createElement('script');
            gtmScript.textContent = `
                (function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
                new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
                j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
                'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
                })(window,document,'script','dataLayer','${data.gtm_tag}');
            `;
            document.head.appendChild(gtmScript);

            // GTM noscript (body)
            const gtmNoscript = document.createElement('noscript');
            const gtmIframe = document.createElement('iframe');
            gtmIframe.src = `https://www.googletagmanager.com/ns.html?id=${data.gtm_tag}`;
            gtmIframe.height = "0";
            gtmIframe.width = "0";
            gtmIframe.style = "display:none;visibility:hidden";

            gtmNoscript.appendChild(gtmIframe);
            document.body.insertBefore(gtmNoscript, document.body.firstChild);

            console.log(`Google Tag Manager (${data.gtm_tag}) успешно добавлен`);
        }
    } catch (error) {
        console.error('Ошибка при вставке аналитики:', error);
        return false;
    }
}
