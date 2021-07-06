import os
from os.path import join, dirname, realpath
import glob
from flask import Flask, render_template, request, flash, send_file
from werkzeug.utils import secure_filename, redirect
from ananse import Ananse

UPLOADS_PATH = join(dirname(realpath(__file__)), 'uploads/')
OUTPUT_PATH = join(dirname(realpath(__file__)), 'outputs/')
ALLOWED_EXTENSIONS = {'txt', 'csv', 'ris'}

app = Flask(__name__)
app.secret_key = "secret key"
app.config['UPLOAD_FOLDER'] = UPLOADS_PATH
app.config['OUTPUT_FOLDER'] = OUTPUT_PATH


def generate_keywords():
    min_len = 2  # minimum keyword length
    max_len = 4  # maximum keyword length

    # Create an instance of the package
    test_run = Ananse()

    # Import your naive search results from the current working directory
    imports = test_run.import_naive_results(path="uploads/", save_dataset=True, save_directory="./outputs/")

    # Columns to deduplicate imported search results
    columns = ['title', 'abstract']

    # De-duplicate the imported search results
    data = test_run.deduplicate_dataframe(imports, columns)

    # Extract keywords from article title and abstract as well as author and database tagged keywords
    all_terms = test_run.extract_terms(data, min_len=min_len, max_len=max_len)

    # Create Document-Term Matrix, with columns as terms and rows as articles
    dtm, term_column = test_run.create_dtm(data.text, keywords=all_terms, min_len=max_len, max_len=max_len)

    # Create co-occurrence network using Document-Term Matrix
    graph_network = test_run.create_network(dtm, all_terms, draw_graph=True)

    # Plot histogram and node strength of the network
    test_run.plot_degree_histogram(graph_network)
    test_run.plot_degree_distribution(graph_network)

    # Determine cutoff for the relevant keywords
    cutoff_strengths = test_run.find_cutoff(
        graph_network,
        "spline",
        "degree",
        degrees=2,
        knot_num=2,
        percent=0.9769956,
        diagnostics=True
    )

    # Get suggested keywords and save to a csv file
    test_run.get_keywords(
        graph_network,
        "degree",
        cutoff_strengths,
        save_keywords=True,
        save_directory="./outputs/"
    )


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/', methods=['GET', 'POST'])
def index():
    response = ''
    if request.method == 'POST':
        if 'file' not in request.files:
            flash('No file part')
            return redirect(request.url)
        files = request.files.getlist('file')
        for file in files:
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))

        generate_keywords()
        files = glob.glob('uploads/*')
        for f in files:
            os.remove(f)

        return redirect('/download-file/relevant_keywords.csv')

    elif request.method == 'GET':
        response = render_template('index.html')

    return response


@app.route("/download-file/<filename>", methods=['GET'])
def download_file(filename):
    return render_template('download.html', value=filename)


@app.route('/downloads/<path:filename>')
def download(filename):
    file_path = OUTPUT_PATH + filename
    return send_file(
        file_path,
        as_attachment=True,
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    # app.run(debug=True, host='0.0.0.0', port=port)
    app.run(debug=True, port=33507)
