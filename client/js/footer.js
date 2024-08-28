(function () {
    'use strict'

    window.onload = function () {
        document.getElementById('return').addEventListener('click', event => {
            window.location.href = './instance.html';
        });
    };
})();