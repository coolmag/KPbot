BOILERS = [
    # 1. Viessmann (Германия) - Эталон надежности
    { 
        "model": "Viessmann Vitopend 100-W A1JB", 
        "power": 24, "price": 105000, "type": "газовый", "area_max": 240,
        "efficiency": 91.0, "circuits": 2, "protocol": "OpenTherm",
        "features": "Защита от колебаний давления газа и напряжения; встроенная самодиагностика",
        "expansion": "Подключение датчиков уличной температуры, Vitoconnect для управления через приложение"
    },
    # 2. Buderus (Германия) - Лучшая адаптация к РФ
    { 
        "model": "Buderus Logamax U072-24K", 
        "power": 24, "price": 85000, "type": "газовый", "area_max": 240,
        "efficiency": 92.0, "circuits": 2, "protocol": "OpenTherm",
        "features": "Работа при падении напряжения до 165В; медный теплообменник",
        "expansion": "Совместим с термостатами серии Logamatic RC"
    },
    # 3. Baxi (Италия) - Самый популярный сервис
    { 
        "model": "BAXI Luna-3 Comfort 240 Fi", 
        "power": 24, "price": 135000, "type": "газовый", "area_max": 240,
        "efficiency": 92.9, "circuits": 2, "protocol": "OpenTherm",
        "features": "Съемная панель управления (служит датчиком температуры); латунная гидравлическая группа",
        "expansion": "Возможность подключения к солнечным коллекторам"
    },
    # 4. Vaillant (Германия) - Премиум сегмент
    { 
        "model": "Vaillant turboTEC plus VUW 242/5-5", 
        "power": 24, "price": 155000, "type": "газовый", "area_max": 240,
        "efficiency": 91.0, "circuits": 2, "protocol": "eBUS",
        "features": "Медный основной теплообменник; расширенная система диагностики",
        "expansion": "Модули vRT для многоконтурных систем отопления"
    },
    # 5. Bosch (Германия) - Массовый стандарт
    { 
        "model": "Bosch Gaz 6000 W WBN-24C", 
        "power": 24, "price": 82000, "type": "газовый", "area_max": 240,
        "efficiency": 93.2, "circuits": 2, "protocol": "OpenTherm",
        "features": "Низкий уровень шума (<36 дБА); стабильная работа при низком давлении газа",
        "expansion": "Подключение регуляторов CR10/CR100"
    },
    # 6. Protherm (Словакия) - Народная марка (Группа Vaillant)
    { 
        "model": "Protherm Гепард 23 MTV", 
        "power": 23, "price": 98000, "type": "газовый", "area_max": 230,
        "efficiency": 91.2, "circuits": 2, "protocol": "eBUS",
        "features": "Режим «Комфорт» для быстрого нагрева ГВС; интуитивное управление",
        "expansion": "Связка с термостатами Exacontrol и системами ZONT"
    },
    # 7. Ariston (Италия) - Технологичность
    { 
        "model": "Ariston Alteas ONE+ NET 24", 
        "power": 24, "price": 142000, "type": "конденсационный", "area_max": 240,
        "efficiency": 107.0, "circuits": 2, "protocol": "BusBridgeNet",
        "features": "Встроенный Wi-Fi; стеклянная фронтальная панель; теплообменник XtraTech из нержавейки",
        "expansion": "Полная интеграция в экосистему Ariston Net"
    },
    # 8. Gassero (Турция/Европа) - Мощность для больших площадей
    { 
        "model": "Gassero Alubox 50", 
        "power": 50, "price": 285000, "type": "конденсационный", "area_max": 500,
        "efficiency": 108.0, "circuits": 1, "protocol": "Modbus / OpenTherm",
        "features": "Литой теплообменник Al-Si-Mg; возможность каскадного подключения до 16 котлов",
        "expansion": "Диспетчеризация через BMS системы"
    },
    # 9. Immergas (Италия) - Компактность
    { 
        "model": "Immergas Maior Eolo 24 4 E", 
        "power": 24, "price": 92000, "type": "газовый", "area_max": 240,
        "efficiency": 93.0, "circuits": 2, "protocol": "IMG Bus (через переходник OpenTherm)",
        "features": "Компактные размеры; возможность установки во влажных помещениях",
        "expansion": "Подключение пульта дистанционного управления Dominus"
    },
    # 10. Wolf (Германия) - Промышленная надежность в быту
    { 
        "model": "Wolf FGB-28", 
        "power": 28, "price": 168000, "type": "конденсационный", "area_max": 280,
        "efficiency": 109.0, "circuits": 2, "protocol": "eBUS",
        "features": "Высокая модуляция пламени (1:6); легкий доступ к узлам для ТО",
        "expansion": "Интеграция с системой автоматики Wolf Smartset"
    }
]