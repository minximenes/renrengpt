(function () {
    'use strict'

    const BUSY_SPINNER = '&nbsp;<span class="spinner-grow spinner-grow-sm"></span>'
    // const SERVICE_RESOURCE = 'http://8.137.83.192:5000';
    const SERVICE_RESOURCE = 'http://127.0.0.1:5000';
    const WAITING_SHOWN_LISTENER = [];

    function $(id) {
        return document.getElementById(id);
    }
    /**
     * button operation
     */
    function gotBusy(btnElem) {
        const btnClass = btnElem.classList;
        btnClass.add('disabled');
        btnElem.innerHTML = btnElem.innerHTML + BUSY_SPINNER;
    }
    function gotNormal(btnElem) {
        const btnClass = btnElem.classList;
        btnClass.remove('disabled');
        btnClass.replace('btn-secondary', 'btn-primary');
        btnElem.innerHTML = btnElem.innerHTML.replace(BUSY_SPINNER, '');
    }
    function gotFinish(btnElem) {
        const btnClass = btnElem.classList;
        btnClass.replace('btn-primary', 'btn-secondary');
        btnElem.innerHTML = btnElem.innerHTML.replace(BUSY_SPINNER, '');
    }
    /**
     * alert msg operation
     */
    /* show alert next to previous div */
    function showAlert(previousDiv, type, msg) {
        switch (type) {
            case 'info':
            case 'danger':
                const container = document.createElement('div');
                container.innerHTML = `
                    <div class="col-sm-12 mb-0 small alert alert-${type} alert-dismissible fade show">
                        <button class="btn btn-close extra-small" data-bs-dismiss="alert"></button>
                        <span class="text-break">${escapeSpecChars(msg)}</span>
                    </div>
                `;
                const newDiv = container.querySelector('div.alert');
                previousDiv.parentNode.insertBefore(newDiv, previousDiv.nextSibling);
                window.scrollTo({top: 0, behavior: 'smooth'});
                return;
            default:
                return;
        }
    }
    function escapeSpecChars(str) {
        return str
            .replace(/\(/g, '&lpar;')
            .replace(/\)/g, '&rpar;');
    }
    /* clear all alerts in target div */
    function clearAlerts(targetDiv) {
        targetDiv.querySelectorAll('div.alert').forEach(
            div => div.parentElement.removeChild(div)
        );
    }
    /**
     * local storage operation
     */
    /* key {value, expire} */
    /* default 30 days */
    function getMilliseconds(hours = 30 * 24) {
        // milliseconds * seconds * minutes
        return 1000 * 60 * 60 * hours;
    }
    function setMeByKey(key) {
        localStorage.setItem(key, JSON.stringify({
            'value': $(key).value,
            'expire': Date.now() + getMilliseconds()
        }));
    }
    function recoverMeByKey(key) {
        $(key).value = '';
        const item = localStorage.getItem(key);
        if (item) {
            const itemjsn = JSON.parse(item);
            if (Date.now() <= itemjsn.expire) {
                $(key).value = itemjsn.value;
                setMeByKey(key);
                return true;
            } else {
                localStorage.removeItem(key);
            }
        }
        return false;
    }
    function setMyKey() {
        setMeByKey('keyid');
        setMeByKey('keysecret');
    }
    function removeMyKey() {
        localStorage.removeItem('keyid');
        localStorage.removeItem('keysecret');
    }
    /* userdatas {seq, name, content} */
    function getUserdatas() {
        const v = localStorage.getItem('userdatas');
        return v ? JSON.parse(v) : v;
    }
    function setUserdatas(v) {
        localStorage.setItem('userdatas', v);
    }
    function removeUserdatas() {
        localStorage.removeItem('userdatas');
    }
    function setUserdata(dataName, dataContent) {
        const newData = {
            seq: Date.now(),
            name: unistrToBase64(dataName),
            content: unistrToBase64(dataContent)
        }
        const oldDatas = getUserdatas();
        const newDatas = oldDatas ? [...oldDatas, newData] : [newData];
        const newDatasStr = JSON.stringify(newDatas);
        localStorage.setItem('userdatas', newDatasStr);
        setUserdatasApi(newDatasStr);
        return newDatas;
    }
    function removeUserdata(seq) {
        const newDatas = getUserdatas().filter(v => v.seq != seq);
        if (newDatas.length > 0) {
            const newDatasStr = JSON.stringify(newDatas);
            localStorage.setItem('userdatas', newDatasStr);
            setUserdatasApi(newDatasStr);
        } else {
            localStorage.removeItem('userdatas');
            removeUserdatasApi();
        }
        return newDatas;
    }
    /* token */
    function setToken(token) {
        localStorage.setItem('token', token);
    }
    function getToken() {
        return localStorage.getItem('token');
    }
    function removeToken() {
        localStorage.removeItem('token');
    }
    /* region in use [] */
    function getRegionInuseOrDefault() {
        const v = localStorage.getItem('regioninuse');
        return v ? JSON.parse(v) : [];
    }
    function setRegionInuse(v) {
        localStorage.setItem('regioninuse', JSON.stringify([...new Set(v)]));
    }
    function removeRegionInuse() {
        localStorage.removeItem('regioninuse');
    }
    function addRegionInuse(v) {
        const oldData = getRegionInuseOrDefault();
        // remove duplicate
        const newData = [...new Set([...oldData, v])]
        localStorage.setItem('regioninuse', JSON.stringify(newData));
    }
    /* regions [] */
    function setRegions(regions) {
        localStorage.setItem('regions', JSON.stringify(regions));
    }
    function getRegions() {
        return JSON.parse(localStorage.getItem('regions'));
    }
    function getRegionsInRange(range) {
        const all = Object.keys(getRegions());
        switch (range) {
            case 'in':
                return all.filter(v => v.startsWith('cn-') && v != 'cn-hongkong');
            case 'out':
                return all.filter(v => !v.startsWith('cn-') || v == 'cn-hongkong');
            case 'us':
            case 'eu':
                return all.filter(v => v.startsWith(`${range}-`));
            case 'neasia':
                return all.filter(v => v.startsWith('ap-northeast-'));
            case 'seasia':
                return all.filter(v => v.startsWith('ap-southeast-'));
            default:
                return [range];
        }
    }

    /**
     * session storage operation
    */
    /* y offset */
    function setPageYOffset(page, offset) {
        sessionStorage.setItem(page, offset);
    }
    function getPageYOffset(page) {
        return sessionStorage.getItem(page) ?? 0;
    }

    /**
     * for init
     */
    function recoverFromStorage() {
        const token = getToken();
        if (token) {
            // user info modal
            getUserdatasApi();
            // main page
            getInstanceListApi();
        } else {
            // login page
            $('rememberme').checked = recoverMeByKey('keyid');
            recoverMeByKey('keysecret');
            naviToPage(['login-page', 'footer']);
        }
    }
    /**
     * page navigation
     */
    function naviToPage(divIDs) {
        endWaiting();
        document.querySelectorAll('div[id$="page"], div[id$="header"], div[id$="footer"]').forEach(
            div => div.classList.add('d-none')
        );
        clearAlerts(document);
        window.scrollTo({top: 0, behavior: 'auto'});

        divIDs.forEach(id => $(id).classList.remove('d-none'));
        // hide back-button
        if ($('instance-list-page').classList.contains('d-none')) {
            $('back-btn').classList.remove('d-none');
        } else {
            $('back-btn').classList.add('d-none');
        }
    }

    /**
     * spinner modal
     */
    function beginWaiting(txt, eventAfterShown) {
        clearAlerts(document);
        $('waiting-modal').addEventListener('shown.bs.modal', eventAfterShown);
        WAITING_SHOWN_LISTENER.push(eventAfterShown);
        $('waiting-modal-txt').innerHTML = txt;
        $('waiting-modal-show').click();
    }
    function endWaiting() {
        if ($('waiting-modal').classList.contains('show')) {
            $('waiting-modal').removeEventListener('shown.bs.modal', WAITING_SHOWN_LISTENER.pop());
            $('waiting-modal-close').click();
        }
    }
    function showWaitingTxt(txt) {
        $('waiting-modal-txt').innerHTML = txt;
    }

    /**
     * login auth
     */
    function authApi() {
        const headers = {'Content-Type': 'application/json'};
        const jsonBody = {
            key_id: $('keyid').value,
            key_secret: $('keysecret').value
        };
        const options = {
            method: 'POST',
            headers: headers,
            body: JSON.stringify(jsonBody)
        };
        fetch(`${SERVICE_RESOURCE}/auth`, options)
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                throw new Error(data.error);
            }
            // token
            setToken(data.token);
            setRegions(data.regions);
            // remember me
            if ($('rememberme').checked) {
                $('keysecret').value = data.key_secret;
                setMyKey();
            } else {
                removeMyKey();
            }
            // userdatas
            getUserdatasApi();
            // instance list
            getRegionInUseApi(Object.keys(data.regions));
        })
        .catch(error => {
            naviToPage(['login-page', 'footer']);
            showAlert($('login-page-nav'), 'danger', error.message);
        });
    }

    /**
     * general handle of api data
     */
    function handleApiData(data) {
        const err = data.error;
        if (err) {
            if (err.startsWith('Authorization')) {
                removeToken();
                throw new Error(`${err} Please refresh and login again.`);
            }
            throw new Error(err);
        }
        // new token
        if (data.new_token) {
            setToken(data.new_token);
        }
    }

    /**
     * get region in use
     */
    function getRegionInUseApi(ids) {
        const token = getToken();
        if (token && ids.length > 0) {
            const left = [...ids];
            const id = left.pop();
            showWaitingTxt(`地域查询&nbsp;${getRegions()[id]}`);

            const headers = {
                'Content-Type': 'application/json',
                'Authorization': token
            };
            const jsonBody = {
                region_ids: [id]
            };
            const options = {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(jsonBody)
            };
            fetch(`${SERVICE_RESOURCE}/instancelist`, options)
            .then(response => response.json())
            .then(data => {
                handleApiData(data);
                data.instances.forEach(v => addRegionInuse(v.region_id));
            })
            .catch(error => {
                showWaitingTxt(`地域查询&nbsp;${getRegions()[id]}&nbsp;<span class="text-danger">error</span>`);
                console.log(error);
            })
            .finally(() => {
                if (left.length > 0) {
                    getRegionInUseApi(left);
                } else {
                    showWaitingTxt('取得实例列表');
                    clearInstanceList();
                    getInstanceListApi();
                }
            });
        }
    }
    /**
     * get instance list
     */
    function getInstanceListApi() {
        const token = getToken();
        if (token) {
            const headers = {
                'Content-Type': 'application/json',
                'Authorization': token
            };
            const jsonBody = {
                region_ids: getRegionInuseOrDefault()
            };
            const options = {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(jsonBody)
            };
            fetch(`${SERVICE_RESOURCE}/instancelist`, options)
            .then(response => response.json())
            .then(data => {
                handleApiData(data);
                // instance list
                clearInstanceList();
                const instances = data.instances;
                const instanceListPageNav = $('instance-list-page-nav');
                if (instanceListPageNav.dataset.new == '1') {
                    renderInstanceList(instances);
                    naviToPage(['nav-header', 'instance-list-page', 'footer']);

                    showAlert(instanceListPageNav, 'info', '实例已成功创建；如果显示不及时请刷新');
                    instanceListPageNav.dataset.new = '0';
                } else {
                    setRegionInuse(instances.map(v => v.region_id));
                    if (instances.length == 0) {
                        renderNoInstance();
                    } else {
                        renderInstanceList(instances);
                        naviToPage(['nav-header', 'instance-list-page', 'footer']);
                    }
                }
            })
            .catch(error => {
                naviToPage(['nav-header', 'instance-list-page', 'footer']);
                showAlert($('instance-list-page-nav'), 'danger', error.message);
            });
        } else {
            naviToPage(['login-page', 'footer']);
        }
    }
    /* render instance list */
    function renderNoInstance() {
        naviToPage(['nav-header', 'instance-list-page', 'footer']);
        showAlert($('instance-list-page-nav'), 'info', '不存在竞价实例');
    }
    function clearInstanceList() {
        $('instance-row').innerHTML = '';
    }
    function renderInstanceList(instances) {
        instances.forEach((v, i) => {
            const container = document.createElement('div');
            container.innerHTML = `
                <div class="card px-0 shadow-sm col-sm-6 border-top-0">
                    <div class="card-body">
                        <table class="table table-borderless mb-0">
                            <tbody>
                                <tr>
                                    <td class="col-5 p-0 text-muted">实例ID</td>
                                    <td class="p-0 extra-small">
                                        <a class="text-decoration-none pointer" id="instanceid-${v.instance_id}"
                                            data-region="${v.region_id}" data-osname="${v.osname}"
                                            data-reltime="${v.release_time}">${v.instance_id}</a>
                                    </td>
                                </tr>
                                <tr>
                                    <td class="p-0 text-muted">状态</td>
                                    <td class="p-0 extra-small">${v.status}</td>
                                </tr>
                                <tr>
                                    <td class="p-0 text-muted">地域</td>
                                    <td class="p-0 extra-small">
                                        <i class="bi bi-geo-alt-fill"></i><span class="mx-1">${getRegions()[v.region_id]}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td class="p-0 text-muted">公网IP</td>
                                    <td class="p-0 extra-small">
                                        <span>${v.pubip_addrs.join()}</span>
                                        <button class="btn btn-outline-secondary btn-sm border-0 p-0" id="ipaddr-${i}"
                                            data-bs-toggle="tooltip" data-bs-title="点击复制">
                                            <i class="bi bi-copy mx-1"></i>
                                        </button>
                                    </td>
                                </tr>
                                <tr>
                                    <td class="p-0 text-muted">
                                        CPU<span class="extra-small">&</span>内存<span class="extra-small">&</span>带宽
                                    </td>
                                    <td class="p-0 extra-small">${getSpecLabel(v)}</td>
                                </tr>
                                <tr>
                                    <td class="p-0 text-muted">创建时间</td>
                                    <td class="p-0 extra-small">${utcToLocalStr(v.creation_time)}</td>
                                </tr>
                                <tr>
                                    <td class="p-0 text-muted">预定释放时间</td>
                                    <td class="p-0 extra-small">
                                        <i class="bi bi-alarm-fill">${utcToLocalStr(v.release_time)}</i>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
            const newDiv = container.querySelector('div.card');
            $('instance-row').appendChild(newDiv);
        });
        // bind event
        $('instance-row').querySelectorAll('a[id^="instanceid-"]').forEach(a => {
            a.addEventListener('click', event => {
                setPageYOffset('instance-list-page', window.scrollY);

                const aElem = event.target;
                $('instance-detail-region').dataset.id = aElem.dataset.region;
                $('instance-detail-id').dataset.id = aElem.textContent;
                beginWaiting('取得实例明细', getInstanceDetailApi);
            });
        });
        $('instance-row').querySelectorAll('button[id^="ipaddr-"]').forEach(btn => {
            btn.addEventListener('click', event => {
                var curElem = event.target;
                while (curElem && curElem.tagName.toLowerCase() != 'td') {
                    curElem = curElem.parentElement;
                }
                copyIp(curElem);
            });
        });
        // tooltip init
        $('instance-row').querySelectorAll('[data-bs-toggle="tooltip"]').forEach(
            i => new bootstrap.Tooltip(i)
        );
    }
    /* utc datetime str to local datetime str */
    function utcToLocalStr(utcstr) {
        if (utcstr) {
            const localDate = new Date(new Date(utcstr).toLocaleString());
            return `${localDate.getMonth() + 1}月${localDate.getDate()}日&nbsp;${localDate.getHours()}:${('0' + localDate.getMinutes()).slice(-2)}`;
        } else {
            return '无';
        }
    }
    /* copy ip to clipboard */
    function copyIp(td) {
        navigator.clipboard.writeText(td.querySelector('span').textContent);
        // IP copied
        const btn = td.querySelector('button');
        const tip = bootstrap.Tooltip.getInstance(`#${btn.id}`);
        tip.setContent({'.tooltip-inner': '已复制到剪贴板'});
        btn.addEventListener('hidden.bs.tooltip', () => {
            tip.setContent({'.tooltip-inner': '点击复制'})
        });
    }
    /**
     * get instance detail
     */
    function getInstanceDetailApi() {
        const token = getToken();
        if (token) {
            const headers = {
                'Content-Type': 'application/json',
                'Authorization': token
            };
            const jsonBody = {
                region_id: $('instance-detail-region').dataset.id,
                instance_id: $('instance-detail-id').dataset.id
            };
            const options = {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(jsonBody)
            };
            fetch(`${SERVICE_RESOURCE}/instancedetail`, options)
            .then(response => response.json())
            .then(data => {
                handleApiData(data);
                // instance detail
                renderInstanceDetail(data.instance);
                naviToPage(['nav-header', 'instance-detail-page', 'footer']);
            })
            .catch(error => {
                naviToPage(['nav-header', 'instance-list-page', 'footer']);
                showAlert($('instance-list-page-nav'), 'danger', error.message);
            });
        } else {
            naviToPage(['login-page', 'footer']);
        }
    }
    /**
     * render instance detail
     */
    function getTypeLabel(v) {
        return v.replace('ecs.', '');
    }
    function getZoneLabel(v) {
        return v.split('-').at(-1).toUpperCase();
    }
    function getSpecLabel(o) {
        return `${o.cpu}vCPU&nbsp;${o.mem}GiB&nbsp;${o.bandwidth}Mbps`;
    }
    function getDiskCategLabel(v) {
        return v.split('_').map(v => cap1stChar(v)).join('&nbsp;');
    }
    function renderInstanceDetail(v) {
        function detail$(id) {
            return $(`instance-detail-${id}`);
        }

        const idElem = detail$('id');
        if (v.status.toLowerCase() == 'running') {
            idElem.innerHTML = `${v.instance_id}<i class="bi bi-check-circle-fill text-success px-1"></i>`;
        } else {
            idElem.innerHTML = `${v.instance_id}<i class="bi bi-stop-circle text-secondary px-1"></i>`;
        }
        idElem.dataset.id = v.instance_id;

        const regionElem = detail$('region');
        regionElem.textContent = getRegions()[v.region_id];
        regionElem.dataset.id = v.region_id;

        detail$('zone').textContent = getZoneLabel(v.zone_id);
        detail$('ipaddr').textContent = v.pubip_addrs.join();
        detail$('type').textContent = getTypeLabel(v.instance_type);
        detail$('spec').innerHTML = getSpecLabel(v);
        detail$('sysdisk').innerHTML = `${v.disk_size}GiB&nbsp;${getDiskCategLabel(v.disk_category)}`;
        detail$('price').innerHTML = `${v.price > 0 ? v.price : '-'}&nbsp;元/小时`;
        detail$('cretime').innerHTML = utcToLocalStr(v.creation_time);

        const listTarget = $(`instanceid-${v.instance_id}`);
        detail$('osname').textContent = listTarget.dataset.osname;
        detail$('reltime').innerHTML = utcToLocalStr(listTarget.dataset.reltime);

        const logElem = detail$('log');
        if (v.pubip_addrs.length > 0 && v.user_data) {
            logElem.target = '_blank';
            logElem.href = `http://${v.pubip_addrs[0]}:5000/init-output`;
            logElem.textContent = '查看';
        } else {
            logElem.removeAttribute('target');
            logElem.removeAttribute('href');
            logElem.textContent = '无';
        }
        const userDataElem = detail$('userdata');
        if (v.user_data) {
            userDataElem.innerHTML = `
                <pre class="m-0 prettyprint lang-sh linenums pre-scrollable pre-abbr">${base64ToUnistr(v.user_data)}</pre>
            `;
        } else {
            userDataElem.innerHTML = `<pre class="m-0 prettyprint lang-sh pre-abbr">没有自定义数据</pre>`;
        }
        PR.prettyPrint();
        gotNormal($('instance-release-btn'));
    }
    /* capitalize fisrt letter */
    function cap1stChar(str) {
        return str.toLowerCase().replace(/\b[a-z]/g, v => v.toUpperCase());
    }

    /**
     * Base64 encode and decode
     */
    function unistrToBase64(str) {
        const dataUint8Array = (new TextEncoder()).encode(str);
        const binaryStr = Array.from(dataUint8Array, byte => String.fromCharCode(byte)).join('');
        return btoa(binaryStr);
    }
    function base64ToUnistr(base64) {
        const binaryStr = atob(base64);
        const dataUint8Array = Uint8Array.from(Array.from(binaryStr, char => char.charCodeAt(0)));
        return (new TextDecoder('utf-8')).decode(dataUint8Array);
    }

    /**
     * release instance
     */
    function releaseInstanceApi(regionid, instanceid) {
        const token = getToken();
        if (token) {
            const headers = {
                'Content-Type': 'application/json',
                'Authorization': token
            };
            const jsonBody = {
                region_id: regionid,
                instance_id: instanceid
            };
            const options = {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(jsonBody)
            };
            fetch(`${SERVICE_RESOURCE}/releaseinstance`, options)
            .then(response => response.json())
            .then(data => {
                handleApiData(data);
                // released
                const biClass = $('instance-detail-id').querySelector('i.bi').classList;
                biClass.add('bi-x-circle-fill');
                biClass.replace('text-success', 'text-secondary');
                gotFinish($('instance-release-btn'));
                showAlert($('instance-detail-page-nav'), 'info', '实例已成功释放');
            })
            .catch(error => {
                showAlert($('instance-detail-page-nav'), 'danger', error.message);
                gotNormal($('instance-release-btn'));
            });
        } else {
            naviToPage(['login-page', 'footer']);
        }
    }

    /**
     * render user info modal
     */
    function renderUserInfo() {
        const userinfo = decodeUserInfo();
        // key
        const keyid = userinfo.keyid;
        if (keyid) {
            $('user-key-id').textContent = keyid;
        }
        $('user-clearme').checked = false;
        // user data
        renderUserDataList(userinfo.userdatas);
    }
    /* get user info from storage */
    function decodeUserInfo() {
        const userinfo = {};
        const token = getToken();
        if (token) {
            const playload = JSON.parse(atob(token.split('.')[1]));
            userinfo.keyid = playload.key_id;
        }
        const userdatas = getUserdatas();
        if (userdatas) {
            userinfo.userdatas = userdatas;
        }
        return userinfo;
    }
    /* render user data list area */
    function renderUserDataList(userdatas) {
        // refresh userdata
        $('user-info-modal-body').querySelectorAll('div.card[id^="user-data-"]').forEach(
            div => $('user-info-modal-body').removeChild(div)
        );
        if (userdatas) {
            // sort seq desc
            userdatas.map(n => n.seq).sort((a, b) => b - a).forEach((seq, i) => {
                const v = userdatas.filter(n => n.seq == seq)[0];
                const container = document.createElement('div');
                container.innerHTML = `
                    <div class="card shadow col-sm-12 mt-1" data-seq="${v.seq}" id="user-data-${i}">
                        <div class="card-body">
                            <div class="d-flex">
                                <div class="text-muted" id="user-data-name-${i}">${base64ToUnistr(v.name)}
                                    <button class="btn btn-outline-primary btn-sm border-0" id="userdata-modal-del-${i}">
                                        <i class="bi bi-trash"></i>
                                    </button>
                                </div>
                            </div>
                            <div class="mt-1" id="user-data-content-${i}">
                                <pre class="m-0 prettyprint lang-sh linenums">${base64ToUnistr(v.content)}</pre>
                            </div>
                        </div>
                    </div>
                `;
                const newDiv = container.querySelector('div.card');
                $('user-info-modal-body').appendChild(newDiv);
            });
            PR.prettyPrint();
            // bind event
            $('user-info-modal-body').querySelectorAll('button[id^="userdata-modal-del-"]').forEach(btn => {
                btn.addEventListener('click', event => {
                    const index = event.currentTarget.id.split('-').at(-1);
                    const seq = $(`user-data-${index}`).dataset.seq;
                    // delete
                    const newDatas = removeUserdata(seq);
                    $('user-info-modal-body').removeChild($(`user-data-${index}`));
                    renderUserdataOpArea(newDatas);
                });
            });
        }
        // userdata option
        renderUserdataOpArea(userdatas);
    }

    /**
     * query spec result
     */
    function querySpecResultApi() {
        const token = getToken();
        if (token) {
            const headers = {
                'Content-Type': 'application/json',
                'Authorization': token
            };
            // parameters
            function radio$(name) {
                return $('spec-query-page').querySelector(`input[type="radio"][name="${name}"]:checked`);
            }
            const regionRange = $('region-op').value;
            const cpuOp = radio$('cpu-op')?.value ?? $('cpu-op-other').value;
            const memOp = radio$('mem-op')?.value ?? $('mem-op-other').value;
            const bandwidthOp = radio$('bandwidth-op')?.value ?? $('bandwidth-op-other').value;

            const jsonBody = {
                region_ids: getRegionsInRange(regionRange),
                cpus: cpuOp.split(',').map(v => parseInt(v)),
                mems: memOp.split(',').map(v => parseInt(v)),
                bandwidth: parseInt(bandwidthOp)
            };
            const options = {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(jsonBody)
            };
            fetch(`${SERVICE_RESOURCE}/speclist`, options)
            .then(response => response.json())
            .then(data => {
                handleApiData(data);
                // spec result
                const specs = data.specs;
                if (specs.length == 0) {
                    renderNoSpec();
                    return;
                }
                clearSpecResult();
                renderSpecResult(specs);
                naviToPage(['nav-header', 'spec-result-page', 'footer']);
            })
            .catch(error => {
                naviToPage(['nav-header', 'spec-query-page', 'footer']);
                showAlert($('spec-query-page-nav'), 'danger', error.message);
            });
        } else {
            naviToPage(['login-page', 'footer']);
        }
    }

    /**
     * render spec result
    */
    function renderNoSpec() {
        naviToPage(['nav-header', 'spec-query-page', 'footer']);
        showAlert($('spec-query-page-nav'), 'info', '不存在条件符合的规格或当前没有库存');
    }
    function clearSpecResult() {
        $('spec-row').innerHTML = '';
    }
    function renderSpecResult(specs) {
        specs.forEach((v, i) => {
            const container = document.createElement('div');
            container.innerHTML = `
                <div class="card px-0 shadow-sm col-sm-6 border-top-0">
                    <div class="card-body">
                        <table class="table table-borderless mb-0">
                            <tbody>
                                <tr>
                                    <td class="col-5 p-0 text-muted">实例规格<small class="fst-italic mx-1">${i + 1}</small></td>
                                    <td class="p-0 extra-small">
                                        <a class="text-decoration-none pointer" id="spec-type-${i}"
                                            data-jsn=${JSON.stringify(v)}>${getTypeLabel(v.instance_type)}</a>
                                    </td>
                                </tr>
                                <tr>
                                    <td class="p-0 text-muted">地域</td>
                                    <td class="p-0 extra-small">
                                        <i class="bi bi-geo-alt-fill"></i><span class="mx-1">${getRegions()[v.region_id]}</span>
                                    </td>
                                </tr>
                                <tr>
                                    <td class="p-0 text-muted">可用区</td>
                                    <td class="p-0 extra-small">${getZoneLabel(v.zone_id)}</td>
                                </tr>
                                <tr>
                                    <td class="p-0 text-muted">
                                        CPU<span class="extra-small">&</span>内存<span class="extra-small">&</span>带宽
                                    </td>
                                    <td class="p-0 extra-small">${getSpecLabel(v)}</td>
                                </tr>
                                <tr>
                                    <td class="p-0 text-muted">系统盘</td>
                                    <td class="p-0 extra-small">${getDiskCategLabel(v.disk_category)}</td>
                                </tr>
                                <tr>
                                    <td class="p-0 text-muted">目录价</td>
                                    <td class="p-0 extra-small"><span class="text-success">${v.price}</span>&nbsp;元/小时</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            `;
            const newDiv = container.querySelector('div.card');
            $('spec-row').appendChild(newDiv);
        });
        // bind event
        $('spec-row').querySelectorAll('a[id^="spec-type-"]').forEach(a => {
            a.addEventListener('click', event => {
                setPageYOffset('spec-result-page', window.scrollY);

                const aElem = event.target;
                const spec = JSON.parse(aElem.dataset.jsn);
                const index = aElem.id.split('-').at(-1);
                renderCreateInstancePage(spec, parseInt(index));
                naviToPage(['nav-header', 'create-instance-page', 'footer']);
            });
        });
    }

    /**
     * prepare for create instance
     */
    function renderCreateInstancePage(v, i) {
        function create$(id) {
            return $(`create-instance-${id}`);
        }

        const instancetype = create$('type');
        instancetype.textContent = getTypeLabel(v.instance_type);
        instancetype.dataset.jsn = JSON.stringify(v);
        create$('spec-index').textContent = i + 1;
        create$('region').textContent = getRegions()[v.region_id];
        create$('zone').textContent = getZoneLabel(v.zone_id);
        create$('spec').innerHTML = getSpecLabel(v);
        create$('sysdisk').innerHTML = getDiskCategLabel(v.disk_category);
        create$('price').innerHTML = `${v.price}&nbsp;元/小时`;
    }
    /* render userdata option area */
    function renderUserdataOpArea(userdatas) {
        function appendOption(name, content, index) {
            const container = document.createElement('div');
            container.innerHTML = `
                <button class="btn ${index == 0 ? 'btn-primary' : 'btn-outline-primary'} btn-sm min-w60 mb-1 mr-1"
                    data-content="${content}" id="userdata-op-${index}">${name}</button>
            `;
            const newElem = container.querySelector('button');
            $('userdata-op-area').appendChild(newElem);
        }

        if (userdatas?.length > 0) {
            $('userdata-op-area').innerHTML = '';
            appendOption('无', '', 0);
            userdatas.forEach((data, i) => {
                appendOption(base64ToUnistr(data.name), data.content, i + 1);
            });
            // bind event
            $('userdata-op-area').querySelectorAll('button[id^="userdata-op-"]').forEach(btn => {
                btn.addEventListener('click', event => {
                    const curElem = event.target;
                    curElem.parentElement.querySelector('.btn-primary').classList
                        .replace('btn-primary', 'btn-outline-primary');
                    curElem.classList.replace('btn-outline-primary', 'btn-primary');
                });
            });
        } else {
            $('userdata-op-area').innerHTML = `
                <button class="btn btn-outline-primary btn-sm border-0 p-0" data-bs-toggle="modal" data-bs-target="#add-userdata-modal"
                    id="userdata-modal-openlink"><i class="bi bi-plus-circle-fill"></i><span class="mx-1">追加脚本</span>
                </button>
            `;
            $('userdata-modal-openlink').addEventListener('click', event => {
                $('userdata-modal-open').click();
                $('add-userdata-dialog').dataset.from = 'preCreate';
            });
        }
    }
    /**
     * create instance
     */
    function createInstanceApi() {
        const token = getToken();
        if (token) {
            const headers = {
                'Content-Type': 'application/json',
                'Authorization': token
            };
            // parameters
            const typeJsn = JSON.parse($('create-instance-type').dataset.jsn);
            const aliveHour = $('alivehour-op').value;
            const dataContent = $('userdata-op-area').querySelector('.btn-primary')?.dataset.content;

            const jsonBody = {
                ...typeJsn,
                alive_minutes: aliveHour * 60,
                user_data: dataContent ?? '',
            };
            const options = {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(jsonBody)
            };
            fetch(`${SERVICE_RESOURCE}/createinstance`, options)
            .then(response => response.json())
            .then(data => {
                handleApiData(data);
                // created
                showWaitingTxt('取得实例列表');
                addRegionInuse(data.region_id);
                $('instance-list-page-nav').dataset.new = '1';
                getInstanceListApi();
            })
            .catch(error => {
                naviToPage(['nav-header', 'create-instance-page', 'footer']);
                showAlert($('create-instance-page-nav'), 'danger', error.message);
            });
        } else {
            naviToPage(['login-page', 'footer']);
        }
    }

    /**
     * api of userdatas
     */
    function getUserdatasApi() {
        const token = getToken();
        if (token) {
            const headers = {
                'Authorization': token
            };
            const options = {
                method: 'GET',
                headers: headers
            };
            fetch(`${SERVICE_RESOURCE}/getuserdatas`, options)
            .then(response => response.json())
            .then(data => {
                handleApiData(data);
                // userdatas
                const user_datas = data.user_datas;
                if (user_datas) {
                    setUserdatas(user_datas);
                } else {
                    removeUserdatas();
                }
            })
            .catch(error => {
                console.log(error);
            })
            .finally(() => {
                renderUserInfo();
            });
        }
    }
    function setUserdatasApi(datastr) {
        const token = getToken();
        if (token) {
            const headers = {
                'Content-Type': 'application/json',
                'Authorization': token
            };
            const jsonBody = {
                user_datas: datastr
            };
            const options = {
                method: 'POST',
                headers: headers,
                body: JSON.stringify(jsonBody)
            };
            fetch(`${SERVICE_RESOURCE}/setuserdatas`, options)
            .then(response => response.json())
            .then(data => {
                handleApiData(data);
            })
            .catch(error => {
                console.log(error);
            });
        }
    }
    function removeUserdatasApi() {
        const token = getToken();
        if (token) {
            const headers = {
                'Authorization': token
            };
            const options = {
                method: 'GET',
                headers: headers
            };
            fetch(`${SERVICE_RESOURCE}/removeuserdatas`, options)
            .then(response => response.json())
            .then(data => {
                handleApiData(data);
            })
            .catch(error => {
                console.log(error);
            });
        }
    }

    /**
     * window onload
     */
    window.onload = function () {
        // init
        recoverFromStorage();

        /* disable enter keypress */
        document.addEventListener('keypress', event => {
            if (event.key == 'Enter' && event.target.tagName.toLowerCase() != 'textarea') {
                event.preventDefault();
                event.stopPropagation();
            }
        });

        // tooltip init
        document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(
            i => new bootstrap.Tooltip(i)
        );

        // fix navigator.clipboard.writeText when http
        httpClipboardCopy();

        /* visitor */
        $('visitor').addEventListener('click', event => {
            $('keyid').value = 'LTAI5t7LSJCM1dCUszcqCHH4';
            $('keysecret').value = 'gAAAAABmubJsiWADX149JKqoO-EtY-4f4dPRi3RZaftIr8F0mr5IALSe2NTSS50KluAwaHVLqQc7lSK-DhlnyZYI2vsD2eI6x5ueZgVbwv1yb6Fsmc5W8v8=';
        });

        /* input type: search or password */
        $('keysecret').addEventListener('focus', event => event.target.type = "search");
        $('keysecret').addEventListener('blur', event => event.target.type = "password");

        /* login-page summit */
        document.querySelector('#login-page .needs-validation').addEventListener('submit', event => {
            event.preventDefault();
            event.stopPropagation();

            clearAlerts($('login-page'));
            const loginForm = event.currentTarget;
            if (loginForm.checkValidity()) {
                loginForm.classList.remove('was-validated');
                beginWaiting('登录验证', authApi);
            } else {
                loginForm.classList.add('was-validated');
            }
        });

        /**
         * instance detail page
         */
        $('instance-detail-copyip').addEventListener('click', event => {
            var curElem = event.currentTarget.parentElement;
            copyIp(curElem);
        });
        /* release instance */
        $('instance-release-confirm').addEventListener('click', event => {
            clearAlerts($('instance-detail-page'));
            gotBusy($('instance-release-btn'));

            const regionid = $('instance-detail-region').dataset.id;
            const instanceid = $('instance-detail-id').dataset.id;
            releaseInstanceApi(regionid, instanceid);
        });

        /* prepare to query instance spec */
        $('spec-prequery-btn').addEventListener('click', event => {
            setPageYOffset('instance-list-page', window.scrollY);
            naviToPage(['nav-header', 'spec-query-page', 'footer']);
        });

        /**
         * nagi bar
         */
        $('back-btn').addEventListener('click', event => {
            // current page
            const curPageId = document.querySelector('div[id$="page"]:not(.d-none)').id;
            const targetPageId = backNavi()[curPageId];
            if (targetPageId) {
                // instance released
                if (curPageId == 'instance-detail-page' && $('instance-release-btn').classList.contains('disabled')) {
                    beginWaiting('取得实例列表', getInstanceListApi);
                } else {
                    naviToPage(['nav-header', targetPageId, 'footer']);
                    switch (targetPageId) {
                        case 'instance-list-page':
                        case 'spec-result-page':
                            window.scrollTo({top: getPageYOffset(targetPageId), behavior: 'auto'});
                        default:
                            break;
                    }
                }
            }
        });
        $('main-btn').addEventListener('click', event => {
            beginWaiting('取得实例列表', getInstanceListApi);
        });
        /* clear for quit */
        $('user-quit-btn').addEventListener('click', event => {
            if ($('user-clearme').checked) {
                // clear all
                removeMyKey();
                removeUserdatas();
                removeRegionInuse();
            } else {
                // only clear secret
                localStorage.removeItem('keysecret');
            }
            removeToken();
            recoverFromStorage();
        });

        /**
         * userdata modal
         */
        $('userdata-modal-open').addEventListener('click', event => {
            // init
            const addModal = $('add-userdata-modal');
            addModal.querySelectorAll('[id^="user-data-input-"]').forEach(input => input.value = '');
            addModal.classList.remove('was-validated');

            $('add-userdata-dialog').dataset.from = '';
        });
        $('userdata-modal-save').addEventListener('click', event => {
            const addModal = $('add-userdata-modal');
            const hasInvalid = Array.from(addModal.querySelectorAll('[id^="user-data-input-"]'))
                .map(input => input.checkValidity()).includes(false);
            if (hasInvalid) {
                addModal.classList.add('was-validated');
            } else {
                addModal.classList.remove('was-validated');
                // save
                const newDatas = setUserdata($('user-data-input-name').value, $('user-data-input-content').value);
                renderUserDataList(newDatas);
                $('userdata-modal-close').click();
            }
        });
        $('userdata-modal-close').addEventListener('click', event => {
            if ($('add-userdata-dialog').dataset.from != 'preCreate') {
                $('user-info-btn').click();
            }
        });

        /**
         * spec query option
         */
        $('spec-query-page').querySelectorAll('input[type="radio"][id*="-op-"]').forEach(radio => {
            radio.addEventListener('click', event => {
                // clear other
                const radioid = event.target.id;
                const other = $(`${radioid.split('-').slice(0, -1).join('-')}-other`);
                other.value = '';
                other.classList.remove('bg-primary', 'text-white');
            })
        });
        $('spec-query-page').querySelectorAll('input[type="number"][id$="-op-other"]').forEach(other => {
            other.addEventListener('input', event => {
                // clear radios
                const other = event.target;
                const radioPrefix = `${other.id.split('-').slice(0, -1).join('-')}-`;
                if (other.value) {
                    if (other.value <= 0) {
                        other.value = 1;
                    }
                    other.classList.add('bg-primary', 'text-white');
                    $('spec-query-page').querySelectorAll(`input[type="radio"][id^="${radioPrefix}"]`).forEach(
                        radio => radio.checked = false
                    );
                } else {
                    $(`${radioPrefix}default`).click();
                }
            })
        });
        $('more-region').addEventListener('click', event => {
            const regionOp = $('region-op').value;
            switch (true) {
                case regionOp == 'cn-hongkong':
                    $('tab-out').click();
                    break;
                case regionOp == 'in':
                case regionOp.startsWith('cn-'):
                    // without hongkong
                    $('tab-in').click();
                    break;
                default:
                    $('tab-out').click();
                    break;
            }
            $(regionOp).checked = true;
        });
        $('spec-reset-btn').addEventListener('click', event => {
            $('region-option-modal').querySelector('label.btn[for="eu-west-1"]').click();
            $('cpu-op-default').click();
            $('mem-op-default').click();
            $('bandwidth-op-default').click();
        });
        $('spec-query-btn').addEventListener('click', event => {
            beginWaiting(
                '取得规格列表<br><span class="extra-small">价格查询可能耗时较长<span>',
                querySpecResultApi
            );
        });
        $('region-option-modal').querySelectorAll('label.btn').forEach(btn => {
            btn.addEventListener('click', event => {
                const curTarget = event.currentTarget;
                const regionOpElem = $('region-op');
                regionOpElem.value = curTarget.getAttribute('for');
                regionOpElem.textContent = curTarget.textContent;

                $('region-option-modal-close').click();
            });
        });
        /**
         * create instance
         */
        $('alivehour-op').addEventListener('input', event => {
            $('alivehour-op-txt').innerHTML = `${event.target.value}&nbsp;小时`;
        });
        $('cre-reset-btn').addEventListener('click', event => {
            $('alivehour-op').value = 1;
            $('alivehour-op-txt').innerHTML = `${1}&nbsp;小时`;
            $('userdata-op-0')?.click();
        });
        /* create instance */
        $('instance-create-confirm').addEventListener('click', event => {
            beginWaiting('创建实例', createInstanceApi);
        });
    }

    /**
     * back navigation
     */
    function backNavi() {
        return {
            'instance-detail-page': 'instance-list-page',
            'spec-query-page': 'instance-list-page',
            'spec-result-page': 'spec-query-page',
            'create-instance-page': 'spec-result-page',
        };
    }

    /**
     * navigator.clipboard.writeText donot work when http
     */
    function httpClipboardCopy() {
        if (navigator.clipboard == undefined || navigator.clipboard.writeText == undefined) {
            navigator.clipboard = {
                writeText: function (text) {
                    const input = document.createElement('textarea');
                    input.value = text;
                    document.body.appendChild(input);
                    input.select();
                    try {
                        document.execCommand('copy');
                    }
                    finally {
                        document.body.removeChild(input);
                    }
                }
            }
        }
    }

})();