# 涩涩

<details>

<summary>开源地址</summary>

<https://github.com/madoka315/Aya-setu>

</details>

{% hint style="info" %}
`<>`表示参数任取；`[]`表示参数可以省略。
{% endhint %}

{% hint style="danger" %}
**请节制！**&#x7FA4;主和管理员应在确定群内**无内鬼**时允许使用该功能。
{% endhint %}

#### 该服务默认<mark style="color:green;">启用</mark>

| 指令示例 | 功能说明 |
| --- | --- |
| [来*X*份]涩图 | 发送*X*张从在线缓存的涩图（单次最多5张） |
| 搜[*X*张]涩图 *关键词* | 根据关键词搜索涩图：由于是人工精选图库，结果不会很多。 |

**以下指令群管理员及以上可用**

| 指令示例 | 功能说明 |
| --- | --- |
| setu set *模块* *设置值* [*群号*] | 修改本群的设置（超级用户可用[群号]指定其他群），设置项见下表： |
| setu get [*群号*] | 查看本群或指定群的图源开启状态 |
| setu warehouse | 查询本地仓库图片数量、容量与上限 |

| 设置项 | 取值 | 说明 |
| --- | --- | --- |
| lolicon | <on, off> | 是否开启lolicon图源 |
| lolicon_r18 | <on, off> | 是否开启r18图源 |
| withdraw | *n* | 发出的图片在*n*秒后撤回，设置为0表示不撤回。另外：setu set withdraw 10 会同时开启r18图源（一键R18），setu set withdraw 0 会同时关闭r18图源 |
