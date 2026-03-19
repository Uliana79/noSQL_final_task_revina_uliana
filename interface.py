import pymongo
from datetime import datetime
import time
import random

class ServiceDBInterface:
    def __init__(self, host='192.168.105.11', port=27017):
        try:
            self.client = pymongo.MongoClient(host, port, serverSelectionTimeoutMS=5000)
            self.client.admin.command('ping')
            self.db = self.client['service']
            print(f"Подключено к {host}:{port}, база: service")
        except Exception as e:
            raise ConnectionError(f"Не удалось подключиться к MongoDB: {e}")
    
    
    def show_stats(self):
        collections = ['Users', 'UserSessions', 'EventLogs', 'SupportTickets', 'UserRecommendations', 'ModerationQueue']
        
        print("\nСтатистика")
        print("-"*30)
        for coll_name in collections:
            count = self.db[coll_name].count_documents({})
            print(f"{coll_name}: {count} документов")
    
    
    def find_user(self):
        user_id = input("user_id: ").strip()
        user = self.db.Users.find_one({"user_id": user_id})
        
        if user:
            print(f"\nНайден: {user.get('email')}, {user.get('name')}")
            print(f"Активен: {user.get('is_active')}")
        else:
            print("Не найден")
    
    
    def show_user_sessions(self):
        user_id = input("user_id: ").strip()
        count = self.db.UserSessions.count_documents({"user_id": user_id})
        print(f"Всего сессий: {count}")
        
        if count > 0:
            print("\nПоследние 5 сессий:")
            sessions = self.db.UserSessions.find({"user_id": user_id}).sort("start_time", -1).limit(5)
            
            for sess in sessions:
                print(f"  {sess.get('session_id')}: {sess.get('device')}, "f"действий: {len(sess.get('actions', []))}")
    
    
    def find_open_tickets(self):
        issue_type = input("Тип проблемы (payment/shipping/account_access/refund/technical_issue): ").strip()
        
        count = self.db.SupportTickets.count_documents({"issue_type": issue_type, "status": "open"})
        
        print(f"Открытых тикетов типа '{issue_type}': {count}")
        
        if count > 0:
            tickets = self.db.SupportTickets.find({"issue_type": issue_type, "status": "open"}).limit(5)
            
            for ticket in tickets:
                print(f"  {ticket.get('ticket_id')}: создан {ticket.get('created_at')}")
    
    
    def add_review(self):
        user_id = input("user_id: ").strip()
        product_id = input("product_id: ").strip()
        rating = int(input("rating (1-5): "))
        text = input("review text: ").strip()
        
        last = self.db.ModerationQueue.find_one(sort=[("review_id", -1)])
        if last:
            last_num = int(last['review_id'].split('_')[1])
            new_num = last_num + 1
        else:
            new_num = 1
        
        review_id = f"rev_{str(new_num).zfill(3)}"
        
        review = {
            "review_id": review_id,
            "user_id": user_id,
            "product_id": product_id,
            "review_text": text,
            "rating": rating,
            "moderation_status": "pending",
            "flags": [],
            "submitted_at": datetime.now().isoformat() + 'Z'
        }
        
        result = self.db.ModerationQueue.insert_one(review)
        if result.inserted_id:
            print(f"Отзыв {review_id} добавлен")
    
    
    def update_ticket_status(self):
        ticket_id = input("ticket_id: ").strip()
        new_status = input("new status (open/in_progress/resolved/closed): ").strip()
        
        result = self.db.SupportTickets.update_many({"ticket_id": ticket_id}, {"$set": {"status": new_status, "updated_at": datetime.now().isoformat() + 'Z'}})
        
        if result.modified_count > 0:
            print(f"Статус {ticket_id} обновлен на {new_status}")
        else:
            print("Тикет не найден")
    
    
    def show_recommendations(self):
        user_id = input("user_id: ").strip()
        rec = self.db.UserRecommendations.find_one({"user_id": user_id})
        
        if rec:
            print(f"Рекомендации для {user_id}:")
            for prod in rec.get('recommended_products', []):
                print(f"  - {prod}")
        else:
            print("Рекомендации не найдены")
    
    def show_sharding_info(self):
        try:
            config_db = self.client['config']
            sharded = list(config_db.collections.find({"_id": {"$regex": "^service\\."}}))
            
            print("\nШардированнные коллекции")
            print("-"*30)
            if sharded:
                for coll in sharded:
                    print(f"  {coll['_id']}: ключ {coll.get('key', {})}")
            else:
                print("Шардированных коллекций нет")
                
            stats = self.db.command("dbstats")
            print(f"\nБаза service: {stats['objects']} объектов, {stats['dataSize']} байт")
            
            print("\nШарды:")
            result = self.client.admin.command("listShards")
            for shard in result['shards']:
                print(f"  {shard['_id']}: {shard['host']}")       
        except Exception as e:
            print(f"Ошибка: {e}")
    
    
    
    
    def measure_time(self, operation, name):
        start = time.time()
        result = operation()
        end = time.time()
        duration_ms = (end - start) * 1000
        print(f"  {name}: {duration_ms:.2f} ms")
        return result, duration_ms
    
    def run_performance_test(self):
        print("\n" + "="*60)
        print("ТЕСТИРОВАНИЕ ПРОИЗВОДИТЕЛЬНОСТИ")
        print("="*60)  
       
        self.measure_time(lambda: self.db.Users.count_documents({"user_id": "user_5025"}), "Поиск пользователя 5025")
        
        self.measure_time(lambda: self.db.UserSessions.count_documents({"user_id": "user_5025"}),"Поиск сессий пользователя 5025")
        
        self.measure_time(lambda: self.db.SupportTickets.count_documents({"issue_type": "payment", "status": "open"}), "Поиск открытых тикетов с типом payment")
        
        self.measure_time(lambda: list(self.db.UserSessions.aggregate([{"$group": {"_id": "$device", "count": {"$sum": 1}}}])), "Агрегация по устройствам")
        
        self.measure_time(lambda: self.db.ModerationQueue.count_documents({"moderation_status": "pending"}), "Поиск отзывов на модерации")
        
        self.measure_time(lambda: list(self.db.EventLogs.find().sort("timestamp", -1).limit(50)), "Последние события (50)")
        
        
    
    def test_multiple_queries(self):
        print("\n" + "="*60)
        print("ТЕСТ С МНОГОКРАТНЫМ ВЫПОЛНЕНИЕМ")
        print("="*60)
        
        num_runs = int(input("Количество повторений каждого запроса: ") or "5")
        
        tests = [
            ("Поиск пользователя", lambda: self.db.Users.count_documents({"user_id": "user_5025"})),
            ("Сессии пользователя", lambda: self.db.UserSessions.count_documents({"user_id": "user_5025"})),
            ("Открытые тикеты", lambda: self.db.SupportTickets.count_documents({"issue_type": "payment", "status": "open"}))
        ]
        
        for test_name, test_func in tests:
            times = []
            for i in range(num_runs):
                start = time.time()
                test_func()
                end = time.time()
                times.append((end - start) * 1000)
            
            avg = sum(times) / len(times)
            min_time = min(times)
            max_time = max(times)
            
            print(f"\n{test_name}:")
            print(f"  Среднее: {avg:.2f} ms")
            print(f"  Мин: {min_time:.2f} ms")
            print(f"  Макс: {max_time:.2f} ms")
            print(f"  Разброс: {max_time - min_time:.2f} ms")



    def test_random_users(self):
        print("\n" + "="*60)
        print("ТЕСТ СО СЛУЧАЙНЫМИ ПОЛЬЗОВАТЕЛЯМИ")
        print("="*60)
        
        num_queries = int(input("Количество запросов: ") or "10")
        
        all_users = list(self.db.Users.find({}, {"user_id": 1}))
        user_ids = [u['user_id'] for u in all_users]
                 
        query_types = ['sessions', 'tickets', 'recommendations']
        total_time = 0
        
        for i in range(num_queries):
            user_id = random.choice(user_ids)
            query_type = random.choice(query_types)
            
            start = time.time()
            
            if query_type == 'sessions':
                count = self.db.UserSessions.count_documents({"user_id": user_id})
                result = f"найдено {count} сессий"
            elif query_type == 'tickets':
                count = self.db.SupportTickets.count_documents({"user_id": user_id})
                result = f"найдено {count} тикетов"
            else:
                rec = self.db.UserRecommendations.find_one({"user_id": user_id})
                result = f"рекомендации: {len(rec.get('recommended_products', [])) if rec else 0} товаров"
            
            end = time.time()
            query_time = (end - start) * 1000
            total_time += query_time
            
            print(f"  {i+1}. {user_id} ({query_type}): {query_time:.2f} ms - {result}")
        
        print(f"\nСреднее время на запрос: {total_time/num_queries:.2f} ms")
        
        
        
    def menu(self):
        while True:
            print("\n" + "-"*60)
            print("Меню:")
            print("1. Статистика базы")
            print("2. Найти пользователя")
            print("3. Сессии пользователя")
            print("4. Открытые тикеты")
            print("5. Добавить отзыв")
            print("6. Обновить статус тикета")
            print("7. Рекомендации пользователя")
            print("8. Информация о шардинге")
            print("9.  Тест производительности")
            print("10. Тест с многократным выполнением")
            print("11. Тест со случайными пользователями")
            print("0. Выход")
            
            choice = input("\nВыбор: ").strip()
            
            if choice == '1':
                self.show_stats()
            elif choice == '2':
                self.find_user()
            elif choice == '3':
                self.show_user_sessions()
            elif choice == '4':
                self.find_open_tickets()
            elif choice == '5':
                self.add_review()
            elif choice == '6':
                self.update_ticket_status()
            elif choice == '7':
                self.show_recommendations()
            elif choice == '9':
                self.run_performance_test()
            elif choice == '10':
                self.test_multiple_queries()
            elif choice == '11':
                self.test_random_users()
            elif choice == '8':
                self.show_sharding_info()
            elif choice == '0':
                print("Выход")
                self.client.close()
                break
            else:
                print("Неверный выбор")

if __name__ == "__main__":
    interface = ServiceDBInterface()
    interface.menu()