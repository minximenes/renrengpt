(function () {
    'use strict'

    window.onload = function () {
        document.getElementById('return').addEventListener('click', event => {
            window.location.href = './instance.html';
        });
    };
})();
/* baidu tongji */
var _hmt = _hmt || [];
(function() {
    var hm = document.createElement("script");
    hm.src = "https://hm.baidu.com/hm.js?d27c9f0b668831b7cc71379502d7af8a";
    var s = document.getElementsByTagName("script")[0];
    s.parentNode.insertBefore(hm, s);
})();