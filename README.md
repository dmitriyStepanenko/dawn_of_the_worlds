# Telegram-bot игра "Рассвет миров"

Финальный проект для курса 
[Python Developer. Professional](https://otus.ru/lessons/python-professional/?int_source=courses_catalog&int_term=programming)

# Оглавление
- [Введение](#введение)
- [Детали реализации и принятые решения](#реализация)
  - [Бэк](#бэк)
  - [Фронт](#фронт)
- [Заключение](#Заключение)

# Введение
В далеком 2017 мы с друзьями как-то наткнулись на одну интересную настольную игру.
В этой игре каждый мог стать богом и вместе создать уникальный мир! 
Звучит заманчиво, правда? 
Для тех, кто хочет поиграть, вот 
[правила](https://github.com/dmitriyStepanenko/dawn_of_the_worlds/blob/master/app/data/static/rules.pdf).

Вкратце опишу игровой процесс: 
все игроки выступают в роли богов и по очереди совершают божественные
действия (формируют землю, создают и уничтожают расы, творят чудеса и прочее;
есть целая таблица действий, доступных игрокам). Игроки записывают 
все происходящее и рисуют карту. В итоге получается уникальный мир с 
подробно задокументированной историей.

Вдохновившись, мы стали творить миры! 
В процессе игры мы поняли, что в просто настольном варианте играть в 
нее не очень то удобно. Кроме истории и карты очевидным образом появлялись 
таблицы различных объектов, которые есть в мире, и следить за всем этим было 
очень трудно. Кроме того, слишком много работы ложилось на летописца 
(того, кто записывал историю), хотя действия часто были однотипными. 
Ну и самой главное - это то, что мы тратили наше совместное время 
на придумывание того, что же каждый привнесет в мир. Хотя это индивидуальный процесс
для каждого игрока. 
В итоге наши игры растягивались на много-много часов 
по совершенно необязательным для этого причинам. Так я решился сделать 
более удобный интерфейс для этой игры. 

Для тех, кто хочет сразу код, вот 
[он](https://github.com/dmitriyStepanenko/dawn_of_the_worlds).

# Реализация 
Начнем написание игры с выбора структуры.
Кажется весьма логичным разделить ее на две части: бэк и фронт.
Бэк должен отделить весь функционал и предоставить оболочку, которую бы дергал фронт.
Тогда выбор фронта становится шире и появляется возможность сделать несколько 
разных фронтов, способных существовать одновременно (в теории). 

## Бэк
Давайте рассмотрим, что же из себя представляет бэк этой игры.
Для этого ответим на вопрос: какой функционал есть в игре?
Поскольку игра нацелена на создание фентезийных миров, 
то все сводится к двум вещам - это редактирование карты мира и запись действий игроков.

Структуру бэка я организовал следующим образом:
1) Модель данных и менеджеры для удобного управления данными
2) Хранилище данных
3) Менеджер изображений
4) Контроллер для использования фронтом

Рассмотрим подробно все эти пункты:

### Данные, объекты и управление ими
Для начала вкратце взглянем на 
[модель данных](https://github.com/dmitriyStepanenko/dawn_of_the_worlds/blob/master/app/world_creator/model.py). 
Согласно правилам: есть мир, в котором существуют разные
боги, территории, климатические зоны, расы, города и прочее.
Для каждого типа объекта был заведен свой класс.

Поскольку несколько объектов могут находиться в одной точке мира, 
то было введено понятие слоя. Кроме того, разные объекты имеют 
разные размеры, но все объекты в рамках одного слоя имеют один размер, 
что удобно для рендера карты.

Поскольку игра пошаговая, то существуют раунды и эпохи, 
в рамках которых игроки совершают действия. 
Есть порядок действий игроков в рамках одного раунда, 
и соответственно есть понятие текущего бога-редактора.

Для более удобного управления объектами все функции создания и изменения были 
вынесены в специальные [менеджеры](https://github.com/dmitriyStepanenko/dawn_of_the_worlds/blob/master/app/world_creator/world_manager.py).

Получилось 4 менеджера:
- Базовый
- Менеджер мира 
- Менеджер бога 
- Менеджер расы

### Хранилище данных
Поскольку предположительно миры не будут очень большими, то 
всю модель мира можно сохранять одной json прямо на файловой системе.
Впрочем, структура проекта такая, что файловое хранилище довольно легко 
заменить на базу данных, реализовав методы загрузки и сохранения в БД.

### Менеджер изображений
Все, что связано с отрисовкой изображений, вынесено в специальный менеджер.
Поскольку изображения формируются "на лету" из статических маленьких картинок,
то есть загрузчики этих изображений и несколько функций непосредственно 
для формирования изображений.

### Контроллер
Чтобы изолировать бэк от фронта, все функции, которые будет "дергать" фронт,
вынесены в 
[контроллеры](https://github.com/dmitriyStepanenko/dawn_of_the_worlds/blob/master/app/world_creator/controller.py). 
Контроллеры естественным образом опираются на менеджеры, 
но их структурирование основано на действиях, доступных игрокам.

Таким образом, получилось 5 контроллеров:
- Базовый
- Контроллер мира
- Контроллер бога
- Контроллер действий бога
- Контроллер расы

## Фронт
В первом приближении я выделил несколько критериев для выбора фронта:
1) Я не хотел делать отдельное приложение (хотелось использовать то, что уже есть у всех)
2) В игре должен быть чат
3) Игра должна быть всегда под рукой, чтобы игроки могли когда угодно 
совершать действия (что должно существенно ускорить игровой процесс)

В последнее время я натыкался на другие игры, реализованные в формате 
телеграмм ботов, и поэтому решил, что и для этой игры такой фронт
вполне может подойти.

### Структура бота
В качестве библиотеки, на которой был написан бот, была выбрана 
[aiogram](https://docs.aiogram.dev/en/latest/).
Кажется, она довольно живая (есть пул разработчиков) и асинхронная.
О том, как делать ботов с ее помощью, можно почитать, например, 
[здесь](https://mastergroosha.github.io/telegram-tutorial-2/quickstart/).

Если в двух словах о том, как сделать с ее помощью бота, то это так:
1) Зарегистрировать бота в телеграмме (у BotFather) и получить токен.
2) Токен подставляем в объект Bot
3) Заводим диспетчер и регистрируем в нем все callback 
   (функции, которые будут обрабатывать сообщения и нажатия на клавиши)
4) Запускаем поллинг
5) Последний шаг: запустить 1-4 через asyncio

### Все ли так просто?
Команды или кнопки, что удобнее?
Телеграмм предоставляет несколько разных вариантов 
реализовать управление нашим миром. 
Во-первых, есть команды, их игрок вводит, после чего происходит что-то.
Во-вторых, есть инлайн и обычные кнопки. 

Обычные кнопки сразу было решено не использовать, поскольку они 
остаются на экране пользователя 
даже после нажатия (в лучшем случае прячутся, но можно развернуть), 
но все еще доступны для нажатия. Что не очень интересно, если есть 
последовательность действий, в которой чередуются ввод текста и нажатия кнопок.
Поэтому все кнопки будут инлайн. 
Инлайн кнопки выводятся прямо под сообщением, кроме того, их можно удалять, 
что удобно с точки зрения очистки чата от бесполезных сообщений и кнопок.
Команды было решено использовать по-минимуму, поскольку все любят жать на 
кнопки, а не вводить текст.

Итого, три основных команды:
1) /world_info - получение информации о мире
2) /god_info - получение информации о боге игрока 
(и кнопок для управления богом, если его ход)
3) /cancel - прерывание действий

В нашей игре есть особенности:
1) Игра пошаговая - это значит, что только один игрок может 
нажимать на кнопки, которые будут управлять миром.
2) Есть кнопки, которые выводят информацию и ничего не меняют. 
Они должны быть доступны в любой момент.

Для решения проблем к нам на помощь приходит машина состояний.
Машина состояний позволяет фиксировать состояние каждого игрока. 
Т.е. если пользователь, например, ввел команду /god_info 
и сейчас его ход, то для него устанавливается состояние "start". 
Остальные игроки не смогут попасть в это состояние, поскольку не их ход.
Далее в callback-ах диспетчер из aiogram сам определит, 
находится ли пользователь в нужном состоянии. 

### Тонкое место с которым не смогла справиться машина состояний в одиночку.
До того как игроки начнут игру, они должны создать мир. 
И вообще говоря, никто не мешает двум игрокам одновременно 
начать создавать мир. Что с точки зрения геймплея не очень здорово. 
Хотелось бы заблокировать создание мира для всех, если кто-то уже начал
создавать мир. Здесь пришлось пойти на уловку и проверять при нажатии 
на кнопку "Создать мир", есть ли другие игроки, которые уже нажали на 
аналогичную кнопку (получили какое-то состояние). И дополнительная проблема,
которая поджидала здесь - это то, что api bot telegram (и aiogram соответственно) 
не позволяет получить список всех участников чата. Но зато можно получить 
список всех администраторов чата. И кажется весьма разумным, 
что только администраторы смогут создавать миры.

### Как развернуть
1) Клонируем репозиторий https://github.com/dmitriyStepanenko/dawn_of_the_worlds.
2) Указываем BOT_TOKEN в .env
3) Пишем в консоли ```docker-compose up```

Все, бот локально развернут, можно его найти в телеграмме, 
пригласить в чат и играть.

## Пример игры
Первый делом приглашаем бота в чат.
Далее если ввести команду /world_info (или /god_info) можно будет создать мир.

![Начало](https://github.com/dmitriyStepanenko/dawn_of_the_worlds/raw/some_images/bot_printscreens/start.png)

После нажатия на кнопку "Создать мир" предлагается заполнить различные параметры мира.

![Создание мира](https://github.com/dmitriyStepanenko/dawn_of_the_worlds/raw/some_images/bot_printscreens/world_creation.png)

После того как мир создан можно посмотреть на то, как он выглядит

![Карта мира](https://github.com/dmitriyStepanenko/dawn_of_the_worlds/raw/some_images/bot_printscreens/show_map.png)

Далее введем команду /god_info и создадим бога

![Создание бога](https://github.com/dmitriyStepanenko/dawn_of_the_worlds/raw/some_images/bot_printscreens/create_god.png)

И после того как администратор нажмет кнопку "Начать игру" появятся кнопки 

![Мой бог после начала игры](https://github.com/dmitriyStepanenko/dawn_of_the_worlds/raw/some_images/bot_printscreens/god_info_after_start_game.png)

Нажав на кнопку "Потратить силу" получим набор кнопок с доступными нам божественными 
действиями (сейчас их всего два поскольку сила 7)

![божественные действия](https://github.com/dmitriyStepanenko/dawn_of_the_worlds/raw/some_images/bot_printscreens/spend_force.png)

Для примера изменим климатическую зону в 3 тайле на снег

![добавить климат](https://github.com/dmitriyStepanenko/dawn_of_the_worlds/raw/some_images/bot_printscreens/form_climate.png)

![результат добавления климата](https://github.com/dmitriyStepanenko/dawn_of_the_worlds/raw/some_images/bot_printscreens/end_of_form_climate.png)
# Заключение
Итак, я сделал телеграмм бота, который позволяет играть в "Рассвет миров".
На данный момент есть возможность: 
- создать мир 
- создать бога
- изменять ландшафт и климат
- создавать расы
- изменять мировоззрение рас
- создавать города
- сделать "событие"

Конечно, реализована только часть божественных действий из оригинальных правил, 
однако проект может быть легко расширен до полной версии, что и планирую сделать
в ближайшем будущем. 
Таким образом, можно выделить следующие перспективы развития этого бота:

1) Реализация всех-всех игровых действий.
2) Более красивые карты за счет реализации более крутого сшивателя изображений.
3) Добавление назывателя местностей. Часто два тайла леса, которые 
стоят рядом, имеют одно название, можно предлагать игрокам это название.
4) Автоматическое удаление сообщений бота из чата.
5) Разворачивание бота на heroku и переход от полинга на вебхуки.
