import csv
import io
from datetime import datetime

from flask import Blueprint, jsonify, redirect, render_template, request, send_file, url_for

from ..services.search_service import get_cached_results, search

bp = Blueprint("search", __name__)


@bp.route("/", methods=["GET"])
def index():
    return render_template("index.html")


@bp.route("/search", methods=["GET"])
def search_route():
    query = request.args.get("q", "").strip()
    if not query:
        return jsonify({"query": query, "results": []})

    results = search(query)
    return jsonify({"query": query, "results": [r.to_dict() for r in results]})


@bp.route("/download", methods=["GET"])
def download_route():
    query = request.args.get("q", "").strip()
    if not query:
        return redirect(url_for("search.index", error="クエリを入力してください"))

    cached = get_cached_results(query)
    if cached is None:
        results = search(query)
    else:
        results = cached

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "title",
            "price",
            "source",
            "url",
            "total",
        ]
    )
    for r in results:
        writer.writerow(
            [
                r.title,
                r.price,
                r.source,
                r.url,
                r.total,
            ]
        )

    output.seek(0)
    data = io.BytesIO(output.getvalue().encode("utf-8"))
    filename = f"whisky_results_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"

    return send_file(
        data,
        mimetype="text/csv",
        as_attachment=True,
        download_name=filename,
    )
