from ui.main_window import run_gui
import database

if __name__ == "__main__":
    database.init_db()
    
    print("Запуск інтерфейсу...")
    run_gui()