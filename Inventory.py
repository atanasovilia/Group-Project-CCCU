import sqlite3
from passlib.hash import sha256_crypt
from datetime import datetime
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.gridlayout import GridLayout
from kivy.uix.popup import Popup
from kivy.uix.widget import Widget
from kivy.graphics import Color, Rectangle

#Back button function 
#Functionality 

# Database Functions - Needs more backend and frontend work
def get_db_connection():
    """Establish a connection to the SQLite database."""
    conn = sqlite3.connect('inventory.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database with required tables and a default user."""
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS users
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      username TEXT UNIQUE NOT NULL,
                      password TEXT NOT NULL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS products
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      name TEXT NOT NULL,
                      description TEXT,
                      price REAL)''')
        c.execute('''CREATE TABLE IF NOT EXISTS inventory
                     (product_id INTEGER,
                      quantity INTEGER,
                      FOREIGN KEY (product_id) REFERENCES products(id))''')
        c.execute('''CREATE TABLE IF NOT EXISTS transactions
                     (id INTEGER PRIMARY KEY AUTOINCREMENT,
                      product_id INTEGER,
                      quantity INTEGER,
                      type TEXT,
                      timestamp TEXT,
                      FOREIGN KEY (product_id) REFERENCES products(id))''')
        # Add default user if none exists(user = admin, pass = admin)
        c.execute('SELECT COUNT(*) FROM users')
        if c.fetchone()[0] == 0:
            default_password = sha256_crypt.hash('admin')
            c.execute('INSERT INTO users (username, password) VALUES (?, ?)', ('admin', default_password))
        conn.commit()

# Custom Widgets for Graphs
class Bar(Widget):
    """A single bar in the bar graph."""
    def __init__(self, value, max_value, **kwargs):
        super().__init__(**kwargs)
        self.value = value
        self.max_value = max_value
        self.bind(size=self.update_bar, pos=self.update_bar)

    def update_bar(self, *args):
        self.canvas.clear()
        with self.canvas:
            Color(0, 0, 1)  # Blue
            height = (self.value / self.max_value) * self.height if self.max_value > 0 else 0
            Rectangle(pos=(self.x, self.y), size=(self.width, height))

class BarGraph(BoxLayout):
    """A bar graph displaying data as a series of bars."""
    def __init__(self, data, **kwargs):
        super().__init__(orientation='horizontal', **kwargs)
        self.data = data
        self.update_graph()

    def update_graph(self):
        self.clear_widgets()
        if not self.data:
            self.add_widget(Label(text='No data'))
            return
        max_value = max(value for _, value in self.data)
        for label, value in self.data:
            bar_container = BoxLayout(orientation='vertical', size_hint_x=None, width=50)
            bar = Bar(value, max_value, size_hint_y=0.8)
            bar_label = Label(text=label, size_hint_y=0.2)
            bar_container.add_widget(bar)
            bar_container.add_widget(bar_label)
            self.add_widget(bar_container)

# Screen Definitions
class LoginScreen(Screen):
    """Login screen for user authentication."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10,)
        layout.add_widget(Label(text='Username'))
        self.username = TextInput(size_hint=(1, None), height=50)
        layout.add_widget(self.username)
        layout.add_widget(Label(text='Password'))
        
        self.password = TextInput(password=True, size_hint=(1, None), height=50 )
        layout.add_widget(self.password)
        login_button = Button(text='Login',size_hint=(1, None), height=50)
        login_button.bind(on_press=self.login)
        layout.add_widget(login_button)
        self.add_widget(layout)
    

    def login(self, instance):
        username = self.username.text
        password = self.password.text
        with get_db_connection() as conn:
            user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and sha256_crypt.verify(password, user['password']): #Password encryption
            self.manager.current = 'dashboard'
        else:
            print('Invalid credentials')  #Needs to be replace with popup in production

class DashboardScreen(Screen):
    """Dashboard screen with navigation options."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        layout.add_widget(Label(text='Dashboard'))
        products_button = Button(text='Products')
        products_button.bind(on_press=lambda x: setattr(self.manager, 'current', 'products'))
        layout.add_widget(products_button)
        inventory_button = Button(text='Inventory')
        inventory_button.bind(on_press=lambda x: setattr(self.manager, 'current', 'inventory'))
        layout.add_widget(inventory_button)
        analytics_button = Button(text='Analytics')
        analytics_button.bind(on_press=lambda x: setattr(self.manager, 'current', 'analytics'))
        layout.add_widget(analytics_button)
        logout_button = Button(text='Logout')
        logout_button.bind(on_press=lambda x: setattr(self.manager, 'current', 'login'))
        layout.add_widget(logout_button)
        self.add_widget(layout)
        
        

class ProductsScreen(Screen):
    """Screen to manage products (add, edit, delete)."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        add_button = Button(text='Add Product', size_hint_y=None, height=50)
        add_button.bind(on_press=self.add_product)
        self.layout.add_widget(add_button)
        self.scrollview = ScrollView()
        self.grid = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.scrollview.add_widget(self.grid)
        self.layout.add_widget(self.scrollview)
        self.add_widget(self.layout)
        layout = BoxLayout(orientation='vertical', padding=10, spacing=10,)
        backButton = Button(text = 'Back', size_hint=(1, None), height=50)
        self.layout.add_widget(backButton)
        backButton.bind (on_press = self.go_back)
    
    def go_back(self, instance):
        """Switch back to the Dashboard screen."""
        self.manager.current = "dashboard"

    def on_pre_enter(self, *args):
        self.load_products()

    def load_products(self):
        self.grid.clear_widgets()
        with get_db_connection() as conn:
            products = conn.execute('SELECT * FROM products').fetchall()
        for product in products:
            product_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
            product_layout.add_widget(Label(text=product['name']))
            edit_button = Button(text='Edit')
            edit_button.bind(on_press=lambda x, p=product: self.edit_product(p))
            product_layout.add_widget(edit_button)
            delete_button = Button(text='Delete')
            delete_button.bind(on_press=lambda x, p=product: self.delete_product(p))
            product_layout.add_widget(delete_button)
            self.grid.add_widget(product_layout)

    def add_product(self, instance):
        self.manager.get_screen('product_form').product_id = None
        self.manager.current = 'product_form'

    def edit_product(self, product):
        self.manager.get_screen('product_form').product_id = product['id']
        self.manager.current = 'product_form'

    def delete_product(self, product):
        with get_db_connection() as conn:
            conn.execute('DELETE FROM products WHERE id = ?', (product['id'],))
            conn.commit()
        self.load_products()

# The Form for the products (Name, Description, Price per unit)
class ProductFormScreen(Screen):
    """Screen for adding or editing a product."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.product_id = None
        layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        layout.add_widget(Label(text='Product Name'))
        self.name_input = TextInput()
        layout.add_widget(self.name_input)
        layout.add_widget(Label(text='Description'))
        self.description_input = TextInput()
        layout.add_widget(self.description_input)
        layout.add_widget(Label(text='Price'))
        self.price_input = TextInput()
        layout.add_widget(self.price_input)
        save_button = Button(text='Save')
        save_button.bind(on_press=self.save_product)
        layout.add_widget(save_button)
        self.add_widget(layout)

    def on_pre_enter(self, *args):
        if self.product_id is not None:
            with get_db_connection() as conn:
                product = conn.execute('SELECT * FROM products WHERE id = ?', (self.product_id,)).fetchone()
            self.name_input.text = product['name']
            self.description_input.text = product['description']
            self.price_input.text = str(product['price'])
        else:
            self.name_input.text = ''
            self.description_input.text = ''
            self.price_input.text = ''

    def save_product(self, instance):
        try:
            name = self.name_input.text.strip()
            description = self.description_input.text.strip()
            price = self.price_input.text.strip()
            
            if not name or not price:
                raise ValueError("Name and price must be filled.")
            
            price = float(price)
            with get_db_connection() as conn:
                if self.product_id is None:
                    c = conn.cursor()
                    c.execute('INSERT INTO products (name, description, price) VALUES (?, ?, ?)', (name, description, price))
                    product_id = c.lastrowid
                    c.execute('INSERT INTO inventory (product_id, quantity) VALUES (?, 0)', (product_id,))
                else:
                    conn.execute('UPDATE products SET name = ?, description = ?, price = ? WHERE id = ?', 
                                 (name, description, price, self.product_id))
                conn.commit()
            self.manager.current = 'products'
        except ValueError as e:
            print(f"Invalid input: {e}")

class InventoryScreen(Screen):
    """Screen to manage inventory (view stock, record transactions)."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = ScrollView()
        self.grid = GridLayout(cols=1, spacing=10, size_hint_y=None)
        self.grid.bind(minimum_height=self.grid.setter('height'))
        self.layout.add_widget(self.grid)
        self.add_widget(self.layout)
        

    def on_pre_enter(self, *args):
        self.load_inventory()

    def load_inventory(self):
        self.grid.clear_widgets()
        with get_db_connection() as conn:
            inventory = conn.execute('SELECT p.name, i.quantity, p.id FROM inventory i JOIN products p ON i.product_id = p.id').fetchall()
        for item in inventory:
            item_layout = BoxLayout(orientation='horizontal', size_hint_y=None, height=50)
            item_layout.add_widget(Label(text=f"{item['name']}: {item['quantity']}"))
            purchase_button = Button(text='Purchase')
            purchase_button.bind(on_press=lambda x, p=item: self.open_transaction_popup(p, 'purchase'))
            item_layout.add_widget(purchase_button)
            sell_button = Button(text='Sold')
            sell_button.bind(on_press=lambda x, p=item: self.open_transaction_popup(p, 'sale'))
            item_layout.add_widget(sell_button)
            self.grid.add_widget(item_layout)

    def open_transaction_popup(self, product, transaction_type):
        popup_layout = BoxLayout(orientation='vertical', padding=10, spacing=10)
        popup_layout.add_widget(Label(text=f"Enter quantity to {transaction_type}"))
        quantity_input = TextInput()
        popup_layout.add_widget(quantity_input)
        save_button = Button(text='Save')
        popup = Popup(title=f"{transaction_type.capitalize()} {product['name']}", content=popup_layout, size_hint=(0.8, 0.4))
        save_button.bind(on_press=lambda x: self.record_transaction(product['id'], transaction_type, quantity_input.text, popup))
        popup_layout.add_widget(save_button)
        popup.open()

    def record_transaction(self, product_id, transaction_type, quantity_str, popup):
        try:
            quantity = int(quantity_str)
            if quantity <= 0:
                raise ValueError("Quantity must be greater than 0.")
            
            with get_db_connection() as conn:
                if transaction_type == 'sale':
                    current_quantity = conn.execute('SELECT quantity FROM inventory WHERE product_id = ?', (product_id,)).fetchone()['quantity']
                    if current_quantity < quantity:
                        print('Not enough stock')
                        return
                    quantity_change = -quantity
                else:
                    quantity_change = quantity

                timestamp = datetime.now().isoformat()
                conn.execute('INSERT INTO transactions (product_id, quantity, type, timestamp) VALUES (?, ?, ?, ?)', 
                             (product_id, quantity, transaction_type, timestamp))
                conn.execute('UPDATE inventory SET quantity = quantity + ? WHERE product_id = ?', (quantity_change, product_id))
                conn.commit()

            popup.dismiss()
            self.load_inventory()

        except ValueError as e:
            print(f"Invalid quantity: {e}")  # Display appropriate error message in the production page(Needs a pop-up)

class AnalyticsScreen(Screen):
    """Screen to display analytics with graphs and availability."""
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.layout = BoxLayout(orientation='vertical', padding=20, spacing=10)
        self.layout.add_widget(Label(text='Analytics'))
        self.bar_graph = BarGraph([('Product 1', 10), ('Product 2', 30), ('Product 3', 20)])
        self.layout.add_widget(self.bar_graph)
        self.add_widget(self.layout)

# App and ScreenManager Setup - Not finished
class MyApp(App):
    def build(self):
        init_db()
        self.manager = ScreenManager()
        self.manager.add_widget(LoginScreen(name='login'))
        self.manager.add_widget(DashboardScreen(name='dashboard'))
        self.manager.add_widget(ProductsScreen(name='products'))
        self.manager.add_widget(ProductFormScreen(name='product_form'))
        self.manager.add_widget(InventoryScreen(name='inventory'))
        self.manager.add_widget(AnalyticsScreen(name='analytics'))
        return self.manager

if __name__ == '__main__':
    MyApp().run()
