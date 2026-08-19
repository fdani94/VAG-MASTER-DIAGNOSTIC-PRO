def _brand_id(con, name):
    r=con.execute('SELECT id FROM brands WHERE name=?',(name,)).fetchone()
    if r:return r[0]
    return con.execute('INSERT INTO brands(name) VALUES(?)',(name,)).lastrowid


def _model_id(con, brand, model):
    bid=_brand_id(con,brand)
    r=con.execute('SELECT id FROM models WHERE brand_id=? AND name=?',(bid,model)).fetchone()
    if r:return r[0]
    return con.execute('INSERT INTO models(brand_id,name) VALUES(?,?)',(bid,model)).lastrowid


def _generation(con, brand, model, name, yf, yt, chassis, platform, url=''):
    mid=_model_id(con,brand,model)
    r=con.execute('SELECT id FROM generations WHERE model_id=? AND name=?',(mid,name)).fetchone()
    if r:return r[0]
    return con.execute('INSERT INTO generations(model_id,name,year_from,year_to,chassis,platform,ross_tech_url) VALUES(?,?,?,?,?,?,?)',
                       (mid,name,yf,yt,chassis,platform,url)).lastrowid


def install(con):
    rows=[
      ('Volkswagen','Golf','VIII CD',2020,2024,'CD','MQB Evo'),
      ('Volkswagen','Passat','B8 3G',2015,2023,'3G','MQB'),
      ('Volkswagen','Passat','B9 CJ',2024,2024,'CJ','MQB Evo'),
      ('Volkswagen','Arteon','3H',2017,2024,'3H','MQB'),
      ('Volkswagen','T-Roc','A1',2017,2024,'A1','MQB A1'),
      ('Volkswagen','T-Cross','C1',2019,2024,'C1','MQB A0'),
      ('Volkswagen','Taigo','CS',2021,2024,'CS','MQB A0'),
      ('Volkswagen','Tiguan','AD/BW',2016,2024,'AD/BW','MQB'),
      ('Volkswagen','Touran','5T',2015,2024,'5T','MQB'),
      ('Volkswagen','Caddy','SB',2020,2024,'SB','MQB'),
      ('Volkswagen','Touareg','CR',2018,2024,'CR','MLB Evo'),
      ('Volkswagen','Transporter','T6/T6.1 SG',2015,2024,'SG','T6'),
      ('Volkswagen','Amarok','2H',2010,2020,'2H','Amarok'),
      ('Volkswagen','ID.3','E1',2020,2024,'E1','MEB'),
      ('Volkswagen','ID.4','E2',2021,2024,'E2','MEB'),
      ('Volkswagen','ID.5','E3',2022,2024,'E3','MEB'),
      ('Audi','A1','GB',2018,2024,'GB','MQB A0'),
      ('Audi','A3','8Y',2020,2024,'8Y','MQB Evo'),
      ('Audi','A4','B9 8W',2016,2024,'8W','MLB Evo'),
      ('Audi','A5','F5',2017,2024,'F5','MLB Evo'),
      ('Audi','A6','C8 4K',2018,2024,'4K','MLB Evo'),
      ('Audi','A7','C8 4K8',2018,2024,'4K8','MLB Evo'),
      ('Audi','A8','D4 4H',2010,2017,'4H','MLB'),
      ('Audi','A8','D5 4N',2018,2024,'4N','MLB Evo'),
      ('Audi','Q2','GA',2016,2024,'GA','MQB'),
      ('Audi','Q3','8U',2011,2018,'8U','PQ35'),
      ('Audi','Q3','F3',2019,2024,'F3','MQB'),
      ('Audi','Q5','FY',2017,2024,'FY','MLB Evo'),
      ('Audi','Q7','4M',2015,2024,'4M','MLB Evo'),
      ('Audi','Q8','4M8',2018,2024,'4M8','MLB Evo'),
      ('Audi','e-tron','GE',2019,2024,'GE','MLB Evo'),
      ('Škoda','Fabia','NJ',2014,2021,'NJ','PQ26'),
      ('Škoda','Fabia','PJ',2021,2024,'PJ','MQB A0'),
      ('Škoda','Rapid','NH',2012,2019,'NH','PQ25'),
      ('Škoda','Scala','NW',2019,2024,'NW','MQB A0'),
      ('Škoda','Kamiq','NW4',2019,2024,'NW4','MQB A0'),
      ('Škoda','Octavia','III 5E',2013,2020,'5E','MQB'),
      ('Škoda','Octavia','IV NX',2020,2024,'NX','MQB Evo'),
      ('Škoda','Superb','III 3V',2015,2024,'3V','MQB'),
      ('Škoda','Karoq','NU',2017,2024,'NU','MQB'),
      ('Škoda','Kodiaq','NS',2017,2024,'NS','MQB'),
      ('Škoda','Enyaq','5A',2021,2024,'5A','MEB'),
      ('SEAT / Cupra','Leon','III 5F',2013,2020,'5F','MQB'),
      ('SEAT / Cupra','Leon','IV KL',2020,2024,'KL','MQB Evo'),
      ('SEAT / Cupra','Ateca','KH',2016,2024,'KH','MQB'),
      ('SEAT / Cupra','Arona','KJ',2017,2024,'KJ','MQB A0'),
      ('SEAT / Cupra','Tarraco','KN',2018,2024,'KN','MQB'),
      ('SEAT / Cupra','Formentor','KM7',2020,2024,'KM7','MQB Evo'),
      ('SEAT / Cupra','Born','K11',2021,2024,'K11','MEB'),
    ]
    for row in rows:_generation(con,*row)
    con.commit()
