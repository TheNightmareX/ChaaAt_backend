# ChaaAt(backend)

第二个 Django + DjangoRESTFramework 项目  
高一作业有点多……更新可能较慢  
依然相当不成熟，如果你发现当前 commit 中有迷惑行为，欢迎通过 issue 告知

目前 Django 的异步生态相当不成熟，只支持异步函数视图，DRF 更是完全不支持异步视图（作者大大说要等 Django 异步成熟后再支持异步  
为了实现我想要的效果，我对 Django 和 DRF 进行了补丁式的修改（通过 mixin），使其支持了异步类视图，如有需要可自取：/drfutils/mixins.py

## 后端部署(Windows 下开发部署)

```
python -m venv venv # 创建虚拟环境
venv\Scripts\activate # 激活虚拟环境
pip install -r requirements.txt # 安装依赖
```

在 ChaaAt_backend 目录下新建 secretsettings.py

```
# secretsettings.py:

SECRET_KEY = 'x&q5tl2ehmw2s(j15$qb(()o4ooati&h=li5ds1n0lvp+xhf^m'
# 生产部署请替换为自己的SECRET_KEY
# 否则攻击者可能得以执行任意代码
```

```
python manage.py migrate # 初始化数据库
python manage.py runserver # 运行开发服务器
```
