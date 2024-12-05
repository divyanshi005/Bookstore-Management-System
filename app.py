from flask import Flask, render_template, request, redirect, url_for, flash
import mysql.connector

app = Flask(__name__)
app.secret_key = 'your_secret_key'  

# Function to connect to the database
def create_connection():
    try:
        connection = mysql.connector.connect(
            host='localhost',
            database='BookStore',
            user='root', 
            password='dh121234' 
        )
        return connection
    except mysql.connector.Error as e:
        print(f"Error: {e}")
        return None

# Index page route
@app.route('/')
def index():
    return render_template('index.html')

# Route for admin login
@app.route('/admin/admin_login/', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        connection = create_connection()
        if not connection:
            flash("Failed to connect to the database.")
            return render_template('/admin/admin_login.html')

        cursor = connection.cursor(dictionary=True)
        query = "SELECT * FROM Admins WHERE username = %s AND password = %s"
        cursor.execute(query, (username, password))
        admin = cursor.fetchone()

        cursor.close()
        connection.close()

        if admin:
            flash("Login successful!")
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid username or password.")
            return render_template('/admin/admin_login.html')
    return render_template('/admin/admin_login.html')

# Admin dashboard home
@app.route('/admin/dashboard')
def admin_dashboard():
    return render_template('/admin/admin_dashboard.html')

#add/ delete books
@app.route('/admin/add_book', methods=['GET', 'POST'])
def add_book():
    if request.method == 'POST':
        if 'delete_book' in request.form:
            # Deleting a book
            book_id = request.form['book_id']
            connection = create_connection()
            cursor = connection.cursor()
            
            # Delete related reviews first to avoid foreign key constraint issues
            delete_reviews_query = "DELETE FROM reviews WHERE book_id = %s"
            cursor.execute(delete_reviews_query, (book_id,))
            connection.commit()
            
            # Now delete the book
            delete_book_query = "DELETE FROM books WHERE book_id = %s"
            cursor.execute(delete_book_query, (book_id,))
            connection.commit()
            
            cursor.close()
            connection.close()
            flash("Book and its associated reviews deleted successfully!")
            return redirect(url_for('add_book'))
        else:
            # Adding a book
            title = request.form['title']
            author = request.form['author']
            genre = request.form['genre']
            price = float(request.form['price'])
            reviews = request.form.get('reviews', None)

            connection = create_connection()
            cursor = connection.cursor()
            add_book_query = "INSERT INTO books (title, author, genre, price) VALUES (%s, %s, %s, %s)"
            cursor.execute(add_book_query, (title, author, genre, price))
            book_id = cursor.lastrowid  # Get the ID of the newly added book for the reviews table
            connection.commit()
            
            if reviews:
                add_review_query = "INSERT INTO reviews (review, book_id) VALUES (%s, %s)"
                cursor.execute(add_review_query, (reviews, book_id))
                connection.commit()
                
            cursor.close()
            connection.close()

            flash("Book added successfully!")
            return redirect(url_for('add_book'))

    # Fetch all books to display in the delete section
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()
    cursor.close()
    connection.close()

    return render_template('/admin/add_book.html', books=books)

# Route for viewing customers (Admin)
@app.route('/admin/dashboard/view_customers', methods=['GET'])
def view_customers():
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)

    # Query to retrieve customer data
    query = "SELECT * FROM Customers"
    cursor.execute(query)
    customers = cursor.fetchall()

    cursor.close()
    connection.close()

    return render_template('/admin/view_customers.html', customers=customers)

# Route for searching books (Admin)
@app.route('/admin/dashboard/search_books', methods=['GET', 'POST'])
def search_books():
    books = []
    if request.method == 'POST':
        query_param = request.form['query_param']
        value = request.form['value']

        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        # Fetch books based on search criteria
        query = f"SELECT * FROM Books WHERE {query_param} LIKE %s"
        cursor.execute(query, (f"%{value}%",))
        books = cursor.fetchall()

        # Fetch reviews for each book and add to the book's dictionary
        for book in books:
            cursor.execute("SELECT review FROM reviews WHERE book_id = %s", (book['book_id'],))
            reviews = cursor.fetchall()
            # Combine reviews into a single string or keep them as a list
            book['reviews'] = [review['review'] for review in reviews]

        cursor.close()
        connection.close()

    return render_template('/admin/search_books.html', books=books)

# Route for viewing transaction history (Admin)
@app.route('/admin/dashboard/transaction_history', methods=['GET'])
def transaction_history():
    connection = create_connection()
    cursor = connection.cursor(dictionary=True)
    
    # Query to retrieve all transaction records, joining with Books to get the price
    query = """
        SELECT tr.transaction_id, tr.book_name, tr.customer_name, tr.purchase_date, b.price
        FROM transactionreceipts tr
        JOIN books b ON tr.book_id = b.book_id
    """
    cursor.execute(query)
    transactions = cursor.fetchall()

    cursor.close()
    connection.close()
    
    return render_template('/admin/transaction_history.html', transactions=transactions)

# Customer dashboard home
@app.route('/customer/dashboard')
def customer_home():
    return render_template('customer/customer_dashboard.html', section='home')

#-----------------------------------------

# when deleting a book, its present as fk 
# in reviews and transaction tables 
#---------------------------------------------

# Route for buying books (Customer)

@app.route('/customer/buy_books', methods=['GET', 'POST'])
@app.route('/customer/buy_books', methods=['GET', 'POST'])
def buy_books():
    if request.method == 'POST':
        customer_name = request.form['customer_name']
        customer_email = request.form['customer_email']
        customer_phone = request.form['customer_phone']
        book_name = request.form['book_name']

        connection = create_connection()
        cursor = connection.cursor(dictionary=True, buffered=True)  # Set buffered=True to handle unread results

        # Check if the customer already exists
        cursor.execute("SELECT * FROM Customers WHERE email = %s", (customer_email,))
        customer = cursor.fetchone()

        if not customer:
            # Insert new customer into the database
            cursor.execute(
                "INSERT INTO Customers (name, email, phone_number) VALUES (%s, %s, %s)",
                (customer_name, customer_email, customer_phone)
            )
            connection.commit()
            customer_id = cursor.lastrowid
            flash(f"New customer created with ID: {customer_id}")
        else:
            customer_id = customer['customer_id']
            flash(f"Existing customer found with ID: {customer_id}")

        # Retrieve the book ID
        get_book_id_query = "SELECT book_id FROM books WHERE title = %s"
        cursor.execute(get_book_id_query, (book_name,))
        book_id_result = cursor.fetchone()

        if not book_id_result:
            flash("Book not found in inventory.")
            cursor.close()
            connection.close()
            return redirect(url_for('buy_books'))

        book_id = book_id_result['book_id']

        # Check if the book is marked as deleted
        cursor.execute("SELECT deleted FROM books WHERE book_id = %s", (book_id,))
        get_del = cursor.fetchone()
        if get_del and get_del['deleted']:
            flash("Book not found in inventory.")
            cursor.close()
            connection.close()
            return redirect(url_for('buy_books'))

        # Insert transaction receipt
        cursor.execute(
            "INSERT INTO TransactionReceipts (customer_name, customer_id, book_name, book_id) VALUES (%s, %s, %s, %s)",
            (customer_name, customer_id, book_name, book_id)
        )
        connection.commit()

        # Delete reviews associated with this book_id
        delete_reviews_query = "DELETE FROM reviews WHERE book_id = %s"
        cursor.execute(delete_reviews_query, (book_id,))
        connection.commit()

        # Mark the book as deleted in the inventory
        cursor.execute("UPDATE books SET deleted = TRUE WHERE book_id = %s", (book_id,))
        connection.commit()

        cursor.close()
        connection.close()
        flash("Transaction recorded successfully!")
        return redirect(url_for('buy_books'))
    
    return render_template('customer/buy_books.html')

# Route for viewing transaction history (Customer)
@app.route('/customer/transaction_history', methods=['GET', 'POST'])
def customer_transaction_history():
    transactions = []
    if request.method == 'POST':
        customer_id = request.form.get('customer_id')
        
        if not customer_id:
            flash("Customer ID is required.")
            return redirect(url_for('customer_transaction_history'))
        
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        # Query to get transaction details, including book price
        cursor.execute("""
            SELECT tr.transaction_id, b.title, tr.purchase_date, b.price
            FROM TransactionReceipts tr
            JOIN Books b ON tr.book_id = b.book_id
            WHERE tr.customer_id = %s
        """, (customer_id,))
        transactions = cursor.fetchall()

        cursor.close()
        connection.close()

    return render_template('customer/transaction_history.html', transactions=transactions)

# Route for searching books (Customer)
@app.route('/customer/customer_search_books', methods=['GET', 'POST'])
def customer_search_books():
    if request.method == 'POST':
        book_name = request.form.get('book_name')
        
        connection = create_connection()
        cursor = connection.cursor(dictionary=True)
        if not book_name:
            flash("Book name is required.")
            return render_template('/customer/customer_search_books.html')
        # Query for the book details
        book_query = "SELECT * FROM Books WHERE title = %s"
        cursor.execute(book_query, (book_name,))
        book = cursor.fetchone()
        
        reviews = []
        if book:
            # Query for reviews if the book is found
            review_query = "SELECT review FROM Reviews WHERE book_id = %s"
            cursor.execute(review_query, (book['book_id'],))
            reviews = cursor.fetchall()
        
        cursor.close()
        connection.close()
        
        return render_template('/customer/customer_search_books.html', book=book, reviews=reviews, search=book_name)
    
    return render_template('/customer/customer_search_books.html')

# Route for adding a review (Customer)
@app.route('/customer/add_review', methods=['GET', 'POST'])
def add_review():
    if request.method == 'POST':
        #book_id is retrieved by book name if book_name is submitted
        book_name = request.form['book_name']
        review = request.form['review']

        connection = create_connection()
        cursor = connection.cursor(dictionary=True)

        # Get book_id based on the book name
        cursor.execute("SELECT book_id FROM books WHERE title = %s", (book_name,))
        book = cursor.fetchone()

        if not book:
            flash("Book not found.")
            return redirect(url_for('add_review'))
        
        # Insert the review into the Reviews table
        query = "INSERT INTO Reviews (book_id, review) VALUES (%s, %s)"
        cursor.execute(query, (book['book_id'], review))
        connection.commit()

        cursor.close()
        connection.close()
        
        flash("Review added successfully!")
        return redirect(url_for('add_review'))
    return render_template('/customer/add_review.html')

if __name__ == '__main__':
    app.run(debug=True)
