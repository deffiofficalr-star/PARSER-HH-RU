import requests
import csv
import json
import time
import os
from datetime import datetime
from typing import List, Dict, Optional

class HHParser:
    def __init__(self):
        self.base_url = "https://api.hh.ru/vacancies"
        self.vacancies = []
        self.filename = "vacancies.csv"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        if os.path.exists(self.filename):
            os.remove(self.filename)
        
        self.init_csv()
    
    def init_csv(self):
        with open(self.filename, 'w', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                'ID', 'Название', 'Зарплата от', 'Зарплата до', 
                'Валюта', 'Город', 'Компания', 'Опыт', 
                'Дата публикации', 'Ссылка', 'Ключевые навыки'
            ])
    
    def search_vacancies(self, keyword: str, area: int = 1, experience: str = "noExperience", per_page: int = 100) -> List[Dict]:
        print(f"🔍 Ищу вакансии по запросу: {keyword}")
        
        params = {
            'text': keyword,
            'area': area,
            'experience': experience,
            'per_page': per_page,
            'page': 0
        }
        
        all_vacancies = []
        
        while True:
            try:
                response = requests.get(self.base_url, params=params, headers=self.headers)
                response.raise_for_status()
                data = response.json()
                
                items = data.get('items', [])
                if not items:
                    break
                
                all_vacancies.extend(items)
                print(f"   Страница {params['page'] + 1}: {len(items)} вакансий")
                
                if params['page'] >= data.get('pages', 1) - 1:
                    break
                
                params['page'] += 1
                time.sleep(1)
                
            except requests.exceptions.RequestException as e:
                print(f"❌ Ошибка запроса: {e}")
                break
        
        print(f"✅ Найдено вакансий: {len(all_vacancies)}")
        return all_vacancies
    
    def parse_vacancy_details(self, vacancy_id: str) -> Optional[Dict]:
        try:
            url = f"https://api.hh.ru/vacancies/{vacancy_id}"
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json()
        except:
            return None
    
    def process_vacancies(self, vacancies: List[Dict]):
        print(f"📝 Обработка {len(vacancies)} вакансий...")
        
        for i, item in enumerate(vacancies):
            try:
                vacancy_id = item.get('id', '')
                name = item.get('name', 'Без названия')
                
                salary = item.get('salary')
                salary_from = salary.get('from') if salary else None
                salary_to = salary.get('to') if salary else None
                currency = salary.get('currency') if salary else ''
                
                area = item.get('area', {})
                city = area.get('name', 'Не указан')
                
                employer = item.get('employer', {})
                company = employer.get('name', 'Не указана')
                
                experience = item.get('experience', {})
                exp_name = experience.get('name', 'Не указан')
                
                published_at = item.get('published_at', '')
                if published_at:
                    published_at = published_at[:10]
                
                link = item.get('alternate_url', '')
                
                skills = []
                details = self.parse_vacancy_details(vacancy_id)
                if details:
                    key_skills = details.get('key_skills', [])
                    skills = [skill.get('name', '') for skill in key_skills]
                
                self.vacancies.append({
                    'id': vacancy_id,
                    'name': name,
                    'salary_from': salary_from,
                    'salary_to': salary_to,
                    'currency': currency,
                    'city': city,
                    'company': company,
                    'experience': exp_name,
                    'published_at': published_at,
                    'link': link,
                    'skills': skills
                })
                
                self.save_to_csv(self.vacancies[-1])
                
                if (i + 1) % 10 == 0:
                    print(f"   Обработано {i + 1}/{len(vacancies)} вакансий")
                
                time.sleep(0.5)
                
            except Exception as e:
                print(f"⚠️ Ошибка при обработке вакансии: {e}")
                continue
        
        print(f"✅ Сохранено {len(self.vacancies)} вакансий в {self.filename}")
    
    def save_to_csv(self, vacancy: Dict):
        with open(self.filename, 'a', newline='', encoding='utf-8') as file:
            writer = csv.writer(file)
            writer.writerow([
                vacancy.get('id', ''),
                vacancy.get('name', ''),
                vacancy.get('salary_from', ''),
                vacancy.get('salary_to', ''),
                vacancy.get('currency', ''),
                vacancy.get('city', ''),
                vacancy.get('company', ''),
                vacancy.get('experience', ''),
                vacancy.get('published_at', ''),
                vacancy.get('link', ''),
                ', '.join(vacancy.get('skills', []))
            ])
    
    def get_statistics(self) -> Dict:
        if not self.vacancies:
            return {'total': 0}
        
        stats = {
            'total': len(self.vacancies),
            'companies': {},
            'cities': {},
            'experience': {},
            'skills': {},
            'avg_salary_from': 0,
            'avg_salary_to': 0,
            'salary_count': 0
        }
        
        total_from = 0
        total_to = 0
        salary_count = 0
        
        for v in self.vacancies:
            company = v.get('company', 'Не указана')
            city = v.get('city', 'Не указан')
            exp = v.get('experience', 'Не указан')
            
            stats['companies'][company] = stats['companies'].get(company, 0) + 1
            stats['cities'][city] = stats['cities'].get(city, 0) + 1
            stats['experience'][exp] = stats['experience'].get(exp, 0) + 1
            
            for skill in v.get('skills', []):
                if skill:
                    stats['skills'][skill] = stats['skills'].get(skill, 0) + 1
            
            if v.get('salary_from'):
                total_from += v['salary_from']
                total_to += v['salary_to'] if v.get('salary_to') else v['salary_from']
                salary_count += 1
        
        if salary_count > 0:
            stats['avg_salary_from'] = round(total_from / salary_count)
            stats['avg_salary_to'] = round(total_to / salary_count)
            stats['salary_count'] = salary_count
        
        stats['top_companies'] = sorted(stats['companies'].items(), key=lambda x: x[1], reverse=True)[:10]
        stats['top_cities'] = sorted(stats['cities'].items(), key=lambda x: x[1], reverse=True)[:10]
        stats['top_skills'] = sorted(stats['skills'].items(), key=lambda x: x[1], reverse=True)[:15]
        
        return stats
    
    def print_statistics(self):
        stats = self.get_statistics()
        
        if stats['total'] == 0:
            print("📊 Нет данных для статистики")
            return
        
        print("\n" + "="*60)
        print("📊 СТАТИСТИКА ПО ВАКАНСИЯМ")
        print("="*60)
        
        print(f"\n📌 Всего вакансий: {stats['total']}")
        
        if stats.get('salary_count', 0) > 0:
            print(f"💰 Средняя зарплата: от {stats['avg_salary_from']:,} до {stats['avg_salary_to']:,} руб.")
        
        print("\n🏢 Топ-10 компаний:")
        for i, (name, count) in enumerate(stats['top_companies'], 1):
            print(f"   {i}. {name} — {count} вакансий")
        
        print("\n📍 Топ-10 городов:")
        for i, (name, count) in enumerate(stats['top_cities'], 1):
            print(f"   {i}. {name} — {count} вакансий")
        
        print("\n💼 Опыт работы:")
        for exp, count in stats['experience'].items():
            print(f"   • {exp}: {count} вакансий")
        
        print("\n🛠️ Топ-15 навыков:")
        for i, (skill, count) in enumerate(stats['top_skills'], 1):
            print(f"   {i}. {skill} — {count} раз")
        
        print("\n" + "="*60)
    
    def export_to_json(self, filename: str = "vacancies.json"):
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.vacancies, f, ensure_ascii=False, indent=2)
        print(f"✅ Экспортировано в {filename}")


def main():
    print("""
╔═══════════════════════════════════════════════════════════╗
║                                                           ║
║   ██╗  ██╗██╗  ██╗    ██████╗  █████╗ ██████╗ ███████╗  ║
║   ██║  ██║██║  ██║    ██╔══██╗██╔══██╗██╔══██╗██╔════╝  ║
║   ███████║███████║    ██████╔╝███████║██████╔╝███████╗  ║
║   ██╔══██║██╔══██║    ██╔══██╗██╔══██║██╔══██╗╚════██║  ║
║   ██║  ██║██║  ██║    ██║  ██║██║  ██║██║  ██║███████║  ║
║   ╚═╝  ╚═╝╚═╝  ╚═╝    ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝  ╚═╝╚══════╝  ║
║                                                           ║
║              ПАРСЕР ВАКАНСИЙ HH.RU v1.0                   ║
║                                                           ║
╚═══════════════════════════════════════════════════════════╝
    """)
    
    parser = HHParser()
    
    keyword = input("🔍 Введите ключевое слово (например, python): ").strip()
    if not keyword:
        keyword = "python"
        print(f"   Использую значение по умолчанию: {keyword}")
    
    print("\n📌 Выберите регион:")
    print("   1. Москва")
    print("   2. Санкт-Петербург")
    print("   3. Россия (все)")
    area_choice = input("   Введите номер (1-3): ").strip()
    
    area_map = {"1": 1, "2": 2, "3": 113}
    area = area_map.get(area_choice, 1)
    
    print("\n💼 Выберите опыт работы:")
    print("   1. Без опыта")
    print("   2. От 1 до 3 лет")
    print("   3. От 3 до 6 лет")
    print("   4. Более 6 лет")
    exp_choice = input("   Введите номер (1-4): ").strip()
    
    exp_map = {"1": "noExperience", "2": "between1And3", "3": "between3And6", "4": "moreThan6"}
    experience = exp_map.get(exp_choice, "noExperience")
    
    print("\n" + "="*60)
    print("🚀 Начинаю парсинг...")
    print("="*60 + "\n")
    
    vacancies = parser.search_vacancies(keyword, area, experience)
    
    if not vacancies:
        print("❌ Вакансии не найдены.")
        return
    
    parser.process_vacancies(vacancies)
    
    print("\n" + "="*60)
    parser.print_statistics()
    
    export_choice = input("\n📤 Экспортировать в JSON? (y/n): ").strip().lower()
    if export_choice == 'y':
        parser.export_to_json()
    
    print("\n✅ Готово! Файл vacancies.csv сохранён в текущей папке.")


if __name__ == "__main__":
    main()
