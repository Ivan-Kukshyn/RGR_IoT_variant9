from pathlib import Path
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, Rectangle, Circle, FancyArrowPatch, Polygon
import numpy as np
PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUT = PROJECT_ROOT / 'results' / 'figures'
OUT.mkdir(exist_ok=True, parents=True)
plt.rcParams.update({'font.family':'DejaVu Sans','font.size':9,'figure.dpi':160})
NAVY='#17365D'; BLUE='#4472C4'; TEAL='#159E9C'; GREEN='#70AD47'; ORANGE='#ED7D31'; PALE='#EAF2F8'; GRAY='#596579'; LIGHT='#F5F7FA'; RED='#C0504D'

def box(ax, xy, w,h,text, fc=PALE, ec=BLUE, fontsize=9, weight='normal'):
    p=FancyBboxPatch(xy,w,h,boxstyle='round,pad=0.03,rounding_size=0.07',facecolor=fc,edgecolor=ec,linewidth=1.4)
    ax.add_patch(p); ax.text(xy[0]+w/2,xy[1]+h/2,text,ha='center',va='center',fontsize=fontsize,weight=weight,wrap=True)
    return p

def arrow(ax, a,b, color=GRAY, text=None, rad=0.0):
    ar=FancyArrowPatch(a,b,arrowstyle='-|>',mutation_scale=12,color=color,linewidth=1.35,connectionstyle=f'arc3,rad={rad}')
    ax.add_patch(ar)
    if text:
        ax.text((a[0]+b[0])/2,(a[1]+b[1])/2+0.07,text,ha='center',va='bottom',fontsize=8,color=color)

def save(name,title,draw,figsize=(10,5)):
    fig,ax=plt.subplots(figsize=figsize); ax.set_xlim(0,10); ax.set_ylim(0,5); ax.axis('off'); ax.set_title(title,fontsize=14,weight='bold',color=NAVY,pad=14); draw(ax); fig.tight_layout(); fig.savefig(OUT/name,bbox_inches='tight',facecolor='white'); plt.close(fig)

# 1 IoT compatibility layers
def d1(ax):
    labels=[('Пристрої та сенсори','Arduino / ESP32 / давачі'),('Канальний і фізичний рівень','Wi-Fi, Ethernet, IEEE 802.15.4'),('Мережевий рівень','IPv6, 6LoWPAN, маршрутизація'),('Прикладний протокол','MQTT, CoAP, HTTP, Modbus TCP'),('Формат та семантика','JSON, CBOR, SenML, одиниці вимірювання')]
    for i,(a,b) in enumerate(labels):
        y=4.15-i*0.82; box(ax,(1.0,y),8,0.58,a+'\n'+b,fc=[ '#EAF2F8','#E2F0D9','#FFF2CC','#FCE4D6','#E4DFEC'][i],ec=NAVY,fontsize=9,weight='normal')
        if i<4: arrow(ax,(5,y),(5,y-0.22))
    ax.text(9.25,2.5,'сумісність\nна всіх рівнях',ha='center',va='center',color=TEAL,weight='bold',fontsize=9)
save('fig01_layers.png','Рисунок 1.1 – Рівні сумісності IoT-системи',d1,(10,5.4))

# 2 protocol suitability
def d2(ax):
    box(ax,(0.4,2.95),2.6,1.1,'Пристрої з малими\nресурсами',fc='#E2F0D9',ec=GREEN,weight='bold')
    box(ax,(3.7,2.95),2.6,1.1,'Шлюз / брокер / API',fc='#EAF2F8',ec=BLUE,weight='bold')
    box(ax,(7,2.95),2.6,1.1,'Сервер / застосунок',fc='#FFF2CC',ec=ORANGE,weight='bold')
    arrow(ax,(3,3.5),(3.7,3.5),'#70AD47','CoAP / MQTT')
    arrow(ax,(6.3,3.5),(7,3.5),BLUE,'HTTP / MQTT')
    ax.text(1.7,2.2,'CoAP: малий overhead,\nобмежені мережі',ha='center',va='center')
    ax.text(5,2.2,'MQTT: publish/subscribe,\nброкер і топіки',ha='center',va='center')
    ax.text(8.3,2.2,'HTTP: REST API,\nширока сумісність',ha='center',va='center')
    box(ax,(2.2,0.55),5.6,0.7,'Спільні формати даних + документовані одиниці вимірювання',fc='#E4DFEC',ec='#8064A2',weight='bold')
    arrow(ax,(5,2.0),(5,1.25),TEAL)
save('fig02_protocols.png','Рисунок 1.2 – Використання протоколів у типовій IoT-системі',d2)

# 3 standardization cycle
def d3(ax):
    nodes=[(1.2,3.3,'Проблема\nсумісності'),(3.2,4.0,'Вимоги\nдо стандарту'),(6.2,4.0,'Розробка та\nузгодження'),(8.1,3.0,'Публікація\nспецифікації'),(6.0,1.0,'Реалізація\nу пристроях'),(2.8,1.0,'Тестування\nсумісності')]
    for x,y,t in nodes: box(ax,(x,y),1.5,.65,t,fc=LIGHT,ec=BLUE)
    for i in range(len(nodes)):
        x,y,_=nodes[i]; x2,y2,_=nodes[(i+1)%len(nodes)]
        arrow(ax,(x+.75,y+.32),(x2+.75,y2+.32),TEAL)
    ax.text(5,2.55,'зворотний зв’язок\nі оновлення',ha='center',va='center',color=GRAY,weight='bold')
save('fig03_lifecycle.png','Рисунок 1.3 – Цикл стандартизації та перевірки сумісності',d3)

# 4 organizations layered roles
def d4(ax):
    box(ax,(0.6,3.1),4.0,1.1,'IETF\nІнтернет-протоколи та RFC\nIPv6, CoAP, RPL, 6LoWPAN',fc='#EAF2F8',ec=BLUE,weight='bold')
    box(ax,(5.4,3.1),4.0,1.1,'IEEE\nЕлектричні/радіо інтерфейси та MAC\n802.3, 802.11, 802.15.4',fc='#E2F0D9',ec=GREEN,weight='bold')
    box(ax,(2.6,1.1),4.8,1.0,'IoT-пристрій: стандарти різних рівнів\nузгоджуються, а не замінюють одне одного',fc='#FFF2CC',ec=ORANGE,weight='bold')
    arrow(ax,(2.6,3.1),(4,2.1),BLUE); arrow(ax,(7.4,3.1),(6,2.1),GREEN)
save('fig04_bodies.png','Рисунок 1.4 – Різні ролі IETF та IEEE в IoT',d4)

# 5 data representation
def d5(ax):
    box(ax,(0.5,3.0),2.5,1,'Вимірювання\nтемператури = 21.6',fc='#E2F0D9',ec=GREEN)
    box(ax,(3.75,3.0),2.5,1,'JSON\n{"temp_c":21.6}',fc='#EAF2F8',ec=BLUE)
    box(ax,(7.0,3.0),2.5,1,'CBOR / SenML\nкомпактне подання',fc='#FFF2CC',ec=ORANGE)
    arrow(ax,(3.0,3.5),(3.75,3.5)); arrow(ax,(6.25,3.5),(7.0,3.5))
    ax.text(5,1.8,'Щоб значення мало однаковий зміст, треба визначити:',ha='center',weight='bold',color=NAVY)
    ax.text(5,1.2,'назву параметра • одиницю • часову мітку • джерело • якість даних',ha='center',fontsize=10)
save('fig05_formats.png','Рисунок 1.5 – Важливість формату та семантики даних',d5)

# 6 standards map
def d6(ax):
    box(ax,(3.5,3.9),3.0,.65,'IoT-пристрій',fc='#EAF2F8',ec=BLUE,weight='bold')
    box(ax,(0.4,2.45),2.5,.8,'IEEE 802.15.4\nрадіо + MAC',fc='#E2F0D9',ec=GREEN)
    box(ax,(3.75,2.45),2.5,.8,'IETF / IPv6 / CoAP\nмережа й обмін',fc='#FFF2CC',ec=ORANGE)
    box(ax,(7.1,2.45),2.5,.8,'Modbus / MQTT\nприкладний рівень',fc='#FCE4D6',ec=RED)
    arrow(ax,(4.2,3.9),(1.65,3.25)); arrow(ax,(5,3.9),(5,3.25)); arrow(ax,(5.8,3.9),(8.35,3.25))
    box(ax,(2.2,.8),5.6,.75,'Усі рівні мають використовувати узгоджену адресацію, формати та профілі',fc='#E4DFEC',ec='#8064A2',weight='bold')
    arrow(ax,(1.65,2.45),(3.1,1.55)); arrow(ax,(5,2.45),(5,1.55)); arrow(ax,(8.35,2.45),(6.9,1.55))
save('fig06_standard_map.png','Рисунок 1.6 – Як стандарти різних рівнів доповнюють одне одного',d6)

# 7 board schematic compare
def d7(ax):
    # stylized boards, explicitly schematic
    for x,color,label in [(0.8,'#252B36','BeagleBone Black'),(5.5,'#245A3C','Raspberry Pi 4 Model B')]:
        p=FancyBboxPatch((x,2.0),3.5,1.8,boxstyle='round,pad=.04,rounding_size=.15',facecolor=color,edgecolor='#111827',linewidth=1.6); ax.add_patch(p)
        ax.add_patch(Rectangle((x+.95,2.55),1.2,.7,facecolor='#A6A6A6',edgecolor='white'))
        ax.text(x+1.55,2.9,'SoC',ha='center',va='center',color='black',weight='bold')
        for j in range(12):
            ax.add_patch(Circle((x+.25+j*.25,3.65),.045,color='#D9C27F'))
            ax.add_patch(Circle((x+.25+j*.25,2.15),.045,color='#D9C27F'))
        ax.text(x+1.75,1.65,label,ha='center',weight='bold',color=NAVY)
    box(ax,(.6,.35),4.1,.8,'CAN-контролер у SoC\n+ зовнішній CAN-трансивер',fc='#E2F0D9',ec=GREEN,fontsize=9)
    box(ax,(5.25,.35),4.1,.8,'CAN через додатковий SPI/USB\nконтролер і трансивер',fc='#FFF2CC',ec=ORANGE,fontsize=9)
    ax.text(5,4.45,'Схематична ілюстрація, не фотографія плат',ha='center',color=GRAY,style='italic',fontsize=8)
save('fig07_boards.png','Рисунок 1.7 – Порівняння апаратної концепції плат',d7)

# 8 Modbus RTU

def d8(ax):
    box(ax,(.4,2.7),2.3,1,'Raspberry Pi /\nBeagleBone Black',fc='#EAF2F8',ec=BLUE,weight='bold')
    box(ax,(3.8,2.7),2.3,1,'USB–RS-485 або\nUART–RS-485',fc='#FFF2CC',ec=ORANGE,weight='bold')
    box(ax,(7.1,2.7),2.3,1,'Лічильник / PLC\nModbus RTU',fc='#E2F0D9',ec=GREEN,weight='bold')
    arrow(ax,(2.7,3.2),(3.8,3.2)); arrow(ax,(6.1,3.2),(7.1,3.2))
    ax.text(5,1.7,'RS-485: A/B диференціальна пара; адреси вузлів; узгодження лінії;',ha='center')
    ax.text(5,1.2,'контроль помилок і параметри порту мають бути однаковими.',ha='center')
save('fig08_modbus.png','Рисунок 1.8 – Приклад підключення Modbus RTU',d8)

# 9 CAN Bus
def d9(ax):
    ax.plot([1,9],[2.5,2.5],color=TEAL,linewidth=4,solid_capstyle='round')
    for x,name in [(1.8,'Вузол 1'),(4.1,'Вузол 2'),(6.4,'Вузол 3'),(8.0,'Вузол n')]:
        box(ax,(x-.55,3.2),1.1,.6,name,fc='#EAF2F8',ec=BLUE)
        ax.plot([x,x],[2.5,3.2],color=GRAY,linewidth=1.5)
    ax.add_patch(Rectangle((.78,2.28),.12,.45,facecolor=RED,edgecolor=RED)); ax.add_patch(Rectangle((8.94,2.28),.12,.45,facecolor=RED,edgecolor=RED))
    ax.text(.7,1.75,'120 Ω',color=RED,weight='bold'); ax.text(8.5,1.75,'120 Ω',color=RED,weight='bold')
    ax.text(5,1.15,'Лінія CAN-H / CAN-L; термінатори ставлять на двох кінцях шини',ha='center')
save('fig09_can.png','Рисунок 1.9 – Спрощена структура CAN-шини',d9)

# 10 choice logic

def d10(ax):
    box(ax,(3.6,4),2.8,.6,'Потрібна інтеграція з PLC?',fc='#EAF2F8',ec=BLUE,weight='bold')
    box(ax,(.6,2.3),3.6,.9,'Так: BeagleBone Black\n+ трансивер/відповідна cape',fc='#E2F0D9',ec=GREEN)
    box(ax,(5.8,2.3),3.6,.9,'Ні, акцент на сервісах/UI:\nRaspberry Pi 4',fc='#FFF2CC',ec=ORANGE)
    arrow(ax,(4.0,4),(2.4,3.2),GREEN,'так'); arrow(ax,(6.0,4),(7.6,3.2),ORANGE,'ні')
    box(ax,(2.5,.55),5,.75,'Обидві плати можуть працювати з Modbus через адаптер і бібліотеки',fc='#FCE4D6',ec=RED,weight='bold')
    arrow(ax,(2.4,2.3),(4,1.3)); arrow(ax,(7.6,2.3),(6,1.3))
save('fig10_choice.png','Рисунок 1.10 – Орієнтовний вибір плати для промислового шлюзу',d10)

# 11 smart home architecture
def d11(ax):
    box(ax,(.35,3.55),2.3,.7,'DS18B20 × 2\nтемпература',fc='#EAF2F8',ec=BLUE)
    box(ax,(.35,2.5),2.3,.7,'BH1750\nосвітленість',fc='#FFF2CC',ec=ORANGE)
    box(ax,(.35,1.45),2.3,.7,'PIR + PZEM-004T\nрух / потужність',fc='#E2F0D9',ec=GREEN)
    box(ax,(3.5,2.45),2.7,1.2,'ESP32\nзчитування + фільтрація\nправила керування',fc='#E4DFEC',ec='#8064A2',weight='bold')
    box(ax,(7.15,3.35),2.3,.8,'Wi-Fi / MQTT\nшлюз або брокер',fc='#EAF2F8',ec=BLUE)
    box(ax,(7.15,1.85),2.3,.8,'Реле × 2\nсвітло / опалення',fc='#FCE4D6',ec=RED)
    box(ax,(7.15,.45),2.3,.65,'Дашборд / журнал\nенергоспоживання',fc='#E2F0D9',ec=GREEN)
    for y in [3.9,2.85,1.8]: arrow(ax,(2.65,y),(3.5,3.05))
    arrow(ax,(6.2,3.1),(7.15,3.75)); arrow(ax,(6.2,2.65),(7.15,2.25)); arrow(ax,(8.3,3.35),(8.3,1.1),TEAL)
save('fig11_smarthome.png','Рисунок 2.1 – Архітектура енергоефективного розумного будинку',d11)

# 12 relay control algorithm
def d12(ax):
    box(ax,(3.5,4.1),3,.55,'Зчитати сенсори',fc='#EAF2F8',ec=BLUE,weight='bold')
    box(ax,(3.5,3.15),3,.55,'Перевірити якість даних',fc='#EAF2F8',ec=BLUE)
    box(ax,(.3,1.9),3.1,.8,'Tвсередині < 20 °C?\nОпалення ON',fc='#FCE4D6',ec=RED)
    box(ax,(3.5,1.9),3.0,.8,'Рух є і lux < 180?\nСвітло ON',fc='#FFF2CC',ec=ORANGE)
    box(ax,(6.7,1.9),3.0,.8,'Інакше вимкнути\nнепотрібне навантаження',fc='#E2F0D9',ec=GREEN)
    box(ax,(3.5,.55),3,.6,'Зберегти та передати телеметрію',fc='#E4DFEC',ec='#8064A2',weight='bold')
    arrow(ax,(5,4.1),(5,3.7)); arrow(ax,(4.1,3.15),(1.9,2.7),RED); arrow(ax,(5,3.15),(5,2.7),ORANGE); arrow(ax,(5.9,3.15),(8.2,2.7),GREEN)
    arrow(ax,(1.9,1.9),(4,1.15),RED); arrow(ax,(5,1.9),(5,1.15),ORANGE); arrow(ax,(8.2,1.9),(6,1.15),GREEN)
save('fig12_control.png','Рисунок 2.2 – Спрощений алгоритм керування навантаженням',d12)

# 13 SQLite ER diagram
def d13(ax):
    box(ax,(.7,2.4),3.4,1.5,'devices\n• device_id PK\n• sensor_key UNIQUE\n• sensor_type, unit, location',fc='#EAF2F8',ec=BLUE,fontsize=9,weight='bold')
    box(ax,(5.8,2.4),3.5,1.5,'readings\n• reading_id PK\n• device_id FK\n• timestamp, raw_value\n• clean_value, quality_flag',fc='#E2F0D9',ec=GREEN,fontsize=9,weight='bold')
    arrow(ax,(4.1,3.15),(5.8,3.15),TEAL,'1 → many')
    ax.text(5,1.55,'Один сенсор може мати багато часових вимірювань. Зовнішній ключ зберігає зв’язок.',ha='center')
save('fig13_sqlite.png','Рисунок 3.1 – Структура реляційної бази SQLite',d13)

# 14 data pipeline
def d14(ax):
    labels=[('1. Сенсори','модельні дані'),('2. Edge cleaning','пропуски / аномалії'),('3. SQLite','FK + індекси'),('4. Аналіз','агрегація / графіки'),('5. Стиснення','gzip / zlib / bzip2'),('6. Firebase','віддалене сховище'),('7. Colab','підсумковий звіт')]
    xs=[.15,1.55,2.95,4.35,5.75,7.15,8.55]
    for (a,b),x in zip(labels,xs): box(ax,(x,2.4),1.25,1.15,a+'\n'+b,fc=[ '#EAF2F8','#FFF2CC','#E2F0D9','#FCE4D6','#E4DFEC','#EAF2F8','#E2F0D9'][len([x0 for x0 in xs if x0<x])],ec=BLUE,fontsize=8,weight='bold')
    for i in range(len(xs)-1): arrow(ax,(xs[i]+1.25,2.98),(xs[i+1],2.98),TEAL)
    ax.text(5,1.5,'За відсутності Firebase-реквізитів локальна частина виконується автономно; хмарний крок вмикається конфігурацією.',ha='center',fontsize=8.5)
save('fig14_pipeline.png','Рисунок 3.2 – Конвеєр Edge Computing та хмарної аналітики',d14,(12,5))

# 15 cleaning quality chart placeholder from actual data created by script, read results
try:
 import pandas as pd
 q=pd.read_csv(PROJECT_ROOT / 'results' / 'quality_report.csv')
 fig,ax=plt.subplots(figsize=(8,3.4)); idx=np.arange(len(q)); w=.25
 ax.bar(idx-w,q['raw_missing'],width=w,label='Пропуски',color=BLUE); ax.bar(idx,q['outliers'],width=w,label='Аномалії',color=ORANGE); ax.bar(idx+w,q['repaired'],width=w,label='Виправлено',color=GREEN)
 ax.set_xticks(idx,q['sensor'],rotation=20,ha='right'); ax.set_title('Виявлені проблеми якості модельних даних'); ax.set_ylabel('Кількість'); ax.legend(); ax.grid(axis='y',alpha=.2); fig.tight_layout(); fig.savefig(OUT/'quality_report.png'); plt.close(fig)
except Exception: pass
# 15 protocol + format interoperability contract
def d15(ax):
    box(ax,(.4,3.4),2.5,.7,'Вузол А\nMQTT / JSON',fc='#EAF2F8',ec=BLUE,weight='bold')
    box(ax,(3.75,3.4),2.5,.7,'Шлюз\nвалідація схеми',fc='#FFF2CC',ec=ORANGE,weight='bold')
    box(ax,(7.1,3.4),2.5,.7,'Вузол Б\nHTTP / JSON',fc='#E2F0D9',ec=GREEN,weight='bold')
    arrow(ax,(2.9,3.75),(3.75,3.75),BLUE,'пакет')
    arrow(ax,(6.25,3.75),(7.1,3.75),GREEN,'перетворення')
    box(ax,(1.4,1.15),7.2,.85,'Контракт даних: назви полів, типи, одиниці, час, версія схеми та правила помилок',fc='#E4DFEC',ec='#8064A2',weight='bold')
    arrow(ax,(5,3.4),(5,2.0),TEAL)
save('fig15_contract.png','Рисунок 1.11 – Контракт обміну даними між різними вузлами',d15)

# 16 interoperability test matrix
def d16(ax):
    cols=['Перевірка','Вузол A','Вузол B','Очікуваний результат']
    rows=[['Протокол','MQTT','HTTP через шлюз','Повідомлення доставлене'],['Формат','JSON','JSON','Поля розібрані'],['Одиниці','°C','°C','Значення порівнювані'],['Час','UTC ISO 8601','UTC ISO 8601','Рядки впорядковані'],['Помилка','немає поля','немає поля','Відхилення + запис журналу']]
    ax.axis('off'); tbl=ax.table(cellText=rows,colLabels=cols,cellLoc='center',colLoc='center',loc='center',colWidths=[.17,.18,.22,.33])
    tbl.auto_set_font_size(False); tbl.set_fontsize(8); tbl.scale(1,1.6)
    for (r,c),cell in tbl.get_celld().items():
        if r==0: cell.set_facecolor(NAVY); cell.get_text().set_color('white'); cell.get_text().set_weight('bold')
        elif r%2==0: cell.set_facecolor('#F1F5F9')
        cell.set_edgecolor('#CBD5E1')
save('fig16_testmatrix.png','Рисунок 1.12 – Приклад матриці тестування сумісності',d16,(10,4.5))
# 17 prototype wiring map
def d17(ax):
    box(ax,(3.6,2.1),2.8,1.8,'ESP32 DevKit\nGPIO4 / GPIO21 / 22\nGPIO27 / UART2\nGPIO25 / GPIO26',fc='#E4DFEC',ec='#8064A2',weight='bold')
    left=[(.2,3.75,'DS18B20 ×2\nGPIO4 + 4.7 kΩ pull-up'),(.2,2.65,'BH1750\nSDA=21, SCL=22'),(.2,1.55,'PIR HC-SR501\nOUT=GPIO27')]
    right=[(7.0,3.4,'PZEM-004T\nUART2 RX16 / TX17'),(7.0,2.2,'Relay channel 1\nGPIO25 → light'),(7.0,1.0,'Relay channel 2\nGPIO26 → heating')]
    for x,y,t in left: box(ax,(x,y),2.5,.65,t,fc='#EAF2F8',ec=BLUE,fontsize=8)
    for x,y,t in right: box(ax,(x,y),2.7,.65,t,fc='#FFF2CC',ec=ORANGE,fontsize=8)
    for x,y,t in left: arrow(ax,(x+2.5,y+.32),(3.6,3.0),BLUE)
    for x,y,t in right: arrow(ax,(6.4,2.9),(x,y+.32),ORANGE)
    ax.text(5,.35,'Логічні ланцюги 3,3/5 В; мережеву напругу перемикає лише правильно підібране реле у закритому корпусі.',ha='center',fontsize=8.1,color=RED)
save('fig17_wiring.png','Рисунок 2.3 – Рекомендована карта підключення прототипу',d17,(10,5.5))
# 18 Standards implementation workflow
def d18(ax):
    labels=[('1. Потреба та вимоги','які вузли мають взаємодіяти?'),('2. Вибір стандарту','рівень, версія, обмеження'),('3. Реалізація','бібліотека, прошивка, конфігурація'),('4. Перевірка','тести сумісності й безпеки'),('5. Експлуатація','моніторинг, оновлення версій')]
    coords=[(.4,3.4),(3.6,3.4),(6.8,3.4),(6.8,1.5),(3.6,1.5)]
    for (head,detail),(x,y) in zip(labels,coords): box(ax,(x,y),2.5,.9,head+'\n'+detail,fc=LIGHT,ec=BLUE,fontsize=8.3,weight='bold')
    arrow(ax,(2.9,3.85),(3.6,3.85),TEAL); arrow(ax,(6.1,3.85),(6.8,3.85),TEAL)
    arrow(ax,(8.05,3.4),(8.05,2.4),TEAL); arrow(ax,(6.8,1.95),(6.1,1.95),TEAL)
    arrow(ax,(3.6,1.95),(1.65,1.95),ORANGE,'зворотний зв’язок')
    arrow(ax,(1.65,2.4),(1.65,3.4),ORANGE)
save('fig18_standard_workflow.png','Рисунок 1.9 – Практичний цикл упровадження та супроводу стандарту',d18,(10,4.8))
