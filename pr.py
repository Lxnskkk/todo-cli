"""
TODO CLI - Консольная утилита для управления списком дел
Модульная архитектура, разработана с имитацией командной работы через Git-ветки
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List
import json
import os
import sys
import argparse


# ======================== models.py ========================
@dataclass
class Task:
    """Модель задачи"""
    id: int
    description: str
    completed: bool = False
    created_at: str = None

    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now().isoformat()

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "completed": self.completed,
            "created_at": self.created_at
        }

    @classmethod
    def from_dict(cls, data: dict):
        return cls(
            id=data["id"],
            description=data["description"],
            completed=data.get("completed", False),
            created_at=data.get("created_at")
        )


# ======================== errors.py ========================
class TaskNotFoundError(Exception):
    def __init__(self, task_id: int):
        super().__init__(f"Задача с id {task_id} не найдена")
        self.task_id = task_id


class InvalidTaskIdError(Exception):
    pass


class EmptyDescriptionError(Exception):
    def __init__(self):
        super().__init__("Описание задачи не может быть пустым")


# ======================== storage.py ========================
DATA_FILE = "tasks.json"


def load_tasks() -> List[Task]:
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return [Task.from_dict(item) for item in data]
    except (json.JSONDecodeError, KeyError):
        print("Предупреждение: файл задач повреждён. Создаётся новый.", file=sys.stderr)
        return []


def save_tasks(tasks: List[Task]) -> None:
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump([t.to_dict() for t in tasks], f, indent=2, ensure_ascii=False)


# ======================== commands.py ========================
def _next_id(tasks: List[Task]) -> int:
    return max((t.id for t in tasks), default=0) + 1


def add_task(description: str) -> Task:
    if not description or not description.strip():
        raise EmptyDescriptionError()

    tasks = load_tasks()
    new_id = _next_id(tasks)
    task = Task(id=new_id, description=description.strip())
    tasks.append(task)
    save_tasks(tasks)
    return task


def list_tasks(show_all: bool = False) -> List[Task]:
    tasks = load_tasks()
    if not show_all:
        tasks = [t for t in tasks if not t.completed]
    return tasks


def mark_done(task_id: int) -> Task:
    tasks = load_tasks()
    for task in tasks:
        if task.id == task_id:
            task.completed = True
            save_tasks(tasks)
            return task
    raise TaskNotFoundError(task_id)


def delete_task(task_id: int) -> None:
    tasks = load_tasks()
    original_count = len(tasks)
    new_tasks = [t for t in tasks if t.id != task_id]

    if len(new_tasks) == original_count:
        raise TaskNotFoundError(task_id)

    save_tasks(new_tasks)


def get_statistics() -> dict:
    tasks = load_tasks()
    total = len(tasks)
    completed = sum(1 for t in tasks if t.completed)
    active = total - completed

    return {
        "total": total,
        "completed": completed,
        "active": active,
        "completion_rate": (completed / total * 100) if total > 0 else 0
    }


# ======================== main.py ========================
def print_task(task: Task, show_date: bool = True) -> None:
    status = "[X]" if task.completed else "[ ]"
    date_str = f" ({task.created_at[:10]})" if show_date else ""
    print(f"{status} #{task.id}: {task.description}{date_str}")


def main():
    parser = argparse.ArgumentParser(
        description="TODO CLI - Менеджер задач",
        epilog="Примеры:\n python main.py add \"Купить молоко\"\n python main.py list\n python main.py done 1"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    parser_add = subparsers.add_parser("add", help="Добавить новую задачу")
    parser_add.add_argument("description", type=str, help="Описание задачи")

    parser_list = subparsers.add_parser("list", help="Показать список задач")
    parser_list.add_argument("--all", "-a", action="store_true", help="Показать все задачи")
    parser_list.add_argument("--stats", "-s", action="store_true", help="Показать статистику")

    parser_done = subparsers.add_parser("done", help="Отметить задачу как выполненную")
    parser_done.add_argument("id", type=int, help="ID задачи")

    parser_del = subparsers.add_parser("delete", help="Удалить задачу")
    parser_del.add_argument("id", type=int, help="ID задачи")

    args = parser.parse_args()

    try:
        if args.command == "add":
            task = add_task(args.description)
            print(f"[+] Добавлена задача #{task.id}: {task.description}")

        elif args.command == "list":
            if args.stats:
                stats = get_statistics()
                print("Статистика:")
                print(f" Всего задач: {stats['total']}")
                print(f" Выполнено: {stats['completed']}")
                print(f" Активных: {stats['active']}")
                print(f" Готовность: {stats['completion_rate']:.1f}%")
            else:
                tasks = list_tasks(show_all=args.all)
                if not tasks:
                    if args.all:
                        print("Нет задач")
                    else:
                        print("Нет активных задач (используйте --all чтобы увидеть выполненные)")
                else:
                    header = "Все задачи:" if args.all else "Активные задачи:"
                    print(header)
                    for task in tasks:
                        print_task(task)

        elif args.command == "done":
            task = mark_done(args.id)
            print(f"[V] Задача #{task.id} выполнена: {task.description}")

        elif args.command == "delete":
            delete_task(args.id)
            print(f"[-] Задача #{args.id} удалена")

    except EmptyDescriptionError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)
    except TaskNotFoundError as e:
        print(f"Ошибка: {e}", file=sys.stderr)
        sys.exit(1)
    except ValueError as e:
        print(f"Ошибка ввода: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Непредвиденная ошибка: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()