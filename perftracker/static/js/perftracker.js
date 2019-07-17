if (!Date.prototype.ptGetShortMonth) {
    Date.prototype.ptGetShortMonth = function() {
        return ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'][this.getMonth()];
    }
}

if (!String.prototype.ptFormat) {
    String.prototype.ptFormat = function() {
        var args = arguments;
        return this.replace(/{(\d+)}/g, function(match, number) {
            var n = parseInt(number);
            return typeof args[n] != 'undefined' ? args[n] : '';
    });
  };
}

function pt_date2str(date_str) {
    if (typeof date_str == 'undefined')
        return '';

    var now = new Date();
    var date = new Date(date_str);
    var hrs = date.getHours();
    var mins = date.getMinutes();

    if (date.getFullYear() != now.getFullYear())
        return date.toISOString().substring(0, 10);

    return date.getDate() + ' ' + date.ptGetShortMonth() + ', ' + (hrs < 10 ? '0' + hrs : hrs) + ":" + (mins < 10 ? '0' + mins: mins);
}

function pt_env_node_draw(j, parent_id)
{
    var s = '';
    var parent_tag = '';
    var this_id = j['id'];
    var glyphicon = '';

    if (parent_id)
        parent_tag = "data-tt-parent-id='{0}'".ptFormat(parent_id);

    if (j['node_type'] && j['node_type']['css'])
        glyphicon = j['node_type']['css'];
    else
        glyphicon = "glyphicon glyphicon-list-alt";

    var cpu_info = "";

    cpu_info += !isNaN(parseInt(j['cpus'])) ? "{0} CPUs".ptFormat(j['cpus']) : '';
    cpu_info += j['cpus_topology'] ? " ({0})".ptFormat(j['cpus_topology']) : '';


    s += "<tr data-tt-id='{0}' {1}><td><span class='{2}'></span>{3}</td><td>{4}</td><td>{5}</td></tr>".ptFormat(
             this_id,
             parent_tag,
             glyphicon,
             [
                 "<span class='treetable-node-name'>{0}</span>".ptFormat(j['name']),
                 typeof j['version'] != 'undefined' ? "({0})".ptFormat(j['version']) : '',
             ].filter(function (v) {return v;}).join(' '),
             [
                 j['ip'],
                 j['hostname']
             ].filter(function (v) {return v;}).join(', '),
             [
                 cpu_info,
                 !isNaN(parseInt(j['ram_mb'])) ? "{0} GB RAM".ptFormat((j['ram_mb'] / 1024.0).toFixed(1)) : '',
                 !isNaN(parseInt(j['disk_gb'])) ? "{0} GB Disk".ptFormat(j['disk_gb']) : '',
                 j['params']
             ].filter(function (v) {return v;}).join(', ')
             );

    if (j['children']) {
        for (var i = 0; i < j['children'].length; i++)
            s += pt_env_node_draw(j['children'][i], this_id);
    }

    return s;
}

function pt_draw_ajax_error(err_msg)
{
    return "<span class=pt_ajax_error>" +
             "<span class='glyphicon glyphicon-alert'></span> " +
             "Data load failed: {0}</span>".ptFormat(err_msg)
}

function pt_toggle_env_nodes(el)
{
    if ($(el).html() == "expand all") {
        $(el).parents('table').treetable('expandAll');
        $(el).html("collapse all");
    } else {
        $(el).parents('table').treetable('collapseAll');
        $(el).html("expand all");
    }
    return false;
}

function pt_draw_attribs(attribs)
{
    var j = JSON.parse(attribs);
    var ret = '';
    for(var title in j) {
        if (ret)
            ret += "; ";
        ret += "{0}: {1}".ptFormat(title, j[title]);
    }
    return ret;
}

function pt_draw_links(links)
{
    var j = JSON.parse(links);
    var ret = '';
    for(var title in j) {
        if (ret)
            ret += " | ";
        ret += "<a href='{0}'>{1}</a>".ptFormat(j[title], title);
    }
    return ret;
}

function pt_draw_job_details(d, err_msg)
{
    var s = '';
    var env_node = d.env_node;
    var vms = d.vms;
    var clients = d.clients;

    s += "<div class='pt_slider' id='job_details_slider_{0}'>".ptFormat(d.id)

    if (err_msg) {
        s += "<div class='row'><div class='col-md-12'>";
        s += pt_draw_ajax_error(ptFormat(err_msg));
        s += "</div></div>";
        return s;
    }

    s += "<div class='row'>";

    s += "<div class='pt_obj_management'>" +
         "<a href='#' onclick=\"return pt_job_edit_cb({0})\">Edit</a><span>|</span>".ptFormat(d.id) +
         "<a href='#' onclick=\"return pt_ajax_job_delete({0})\">Delete</a><span>|</span>".ptFormat(d.id) +
         "<a href='/0/job/{0}?as_json=1'>Download JSON</a><span>|</span>".ptFormat(d.id) +
         "<a onclick=\"alert('Sorry, not implemented');return false;\" >Download XLS</a></div>";

    s += "<div class='col-md-12'><h4>Test suite</h4>";
    s += "<table class='pt_obj_details'>";
    s += "<thead><th>Parameter</th><th>Value</th></thead>";

    if (d.product_name)
        s += "<tr><td>Product</td><td><b>{0} {1}</b></td></tr>".ptFormat(d.product_name, d.product_ver)

    if (d.links) {
        var links = pt_draw_links(d.links);
        if (links)
            s += "<tr><td>Links</td><td>{0}</td></tr>".ptFormat(links);
    }

    s += "<tr><td>Job #</td><td>{0}</td></tr>".ptFormat(d.id)
    s += "<tr><td>UUID</td><td>{0}</td></tr>".ptFormat(d.uuid)
    s += "<tr><td>Duration</td><td>{0} - {1} ({2}), uploaded: {3}</td></tr>".ptFormat(
         pt_date2str(d.begin), pt_date2str(d.end), d.duration, pt_date2str(d.upload))
    if (d.cmdline)
        s += "<tr><td>Cmdline</td><td class='pt_ellipsis'>{0}</td></tr>".ptFormat(d.cmdline)

    if (d.artifacts) {
        s += "<tr><td>Artifacts</td><td>";
        var artifacts = [];

        for (var n = 0; n < d.artifacts.length; n++) {
            var a = d.artifacts[n];
            artifacts.push("<a target=_blank href='/0/artifact_content/{0}'>{1}</a>".ptFormat(a.uuid, a.filename));
        }
        s += artifacts.join(" | ");
        s += "</td></tr>";
    }

    s += "</table></div>";
    s += "</div>";

    s += "<div class='row'>";
    s += "<div class='col-md-12'><h4>Environment</h4>";
    s += "<table id='env_nodes_{0}' class='pt_obj_details'>".ptFormat(d.id);
    s += "<thead><th>Nodes (<a href='#' onclick=\"return pt_toggle_env_nodes(this);\">expand all</a>)</th>" +
             "</th><th>Location</th><th>Details</th></thead><tbody>";
    for (var i = 0; i < env_node.length; i++)
        s += pt_env_node_draw(env_node[i], 0);
    s += "</tbody></table></div>";

    s += "</div></div>";

    return s;
}

function pt_ajax_job_details(api_ver, project_id, job_id)
{
    $.ajax({
        url: '/api/v' + api_ver + '/' + project_id + '/job/{0}'.ptFormat(job_id),
        cache: true,
        data: null,
        type: 'GET',
        timeout: 2000,
        success: function(data, status) {
            $('#job_details_{0}'.ptFormat(job_id)).html(pt_draw_job_details(data, null));
            $('#env_nodes_{0}'.ptFormat(job_id)).treetable({expandable: true});
            $('#job_details_slider_{0}'.ptFormat(job_id)).slideDown();
        },
        error: function(data, status, error) {
            $('#job_details_{0}'.ptFormat(job_id)).html(pt_draw_ajax_error(error));
            $('#job_details_slider_{0}'.ptFormat(job_id)).slideDown();
        }
    });
}

function pt_ajax_job_delete(job_id)
{
    if (!confirm('Are you sure you want to delete job #' + job_id + '?'))
        return false;

    $.ajax({
        url: '/api/v1.0/0/job/{0}'.ptFormat(job_id),
        cache: true,
        data: null,
        type: 'DELETE',
        timeout: 2000,
        success: function(data, status) {
            window.location.reload();
        },
        error: function(data, status, error) {
            alert("can't delete job #" + job_id + ", " + error);
        }
    });
    return false;
}

function pt_draw_comparison_details(d, err_msg)
{
    var s = '';
    var env_node = d.env_node;
    var vms = d.vms;
    var clients = d.clients;

    s += "<div class='pt_slider' id='comparison_details_slider_{0}'>".ptFormat(d.id)

    if (err_msg) {
        s += "<div class='row'><div class='col-md-12'>";
        s += pt_draw_ajax_error(ptFormat(err_msg));
        s += "</div></div>";
        return s;
    }

    s += "<div class='row'>";

    s += "<div class='pt_obj_management'>" +
         "<a onclick=\"window.location.replace('/{0}/job/?edit={1}');return false;\" >Edit</a><span>|</span>".ptFormat(d.project.id, d.id) +
         "<a href='#' onclick=\"return pt_ajax_comparison_delete({0})\">Delete</a><span>|</span>".ptFormat(d.id) +
         "<a onclick=\"alert('Sorry, not implemented');return false;\" >Download XLS</a></div>";

    s += "<div class='col-md-12'><h4>Jobs</h4>";
    s += "<table class='pt_obj_details'>";
    s += "<thead><th>#</th><th>Job end</th><th>Hw</th><th>Version</th><th>Title</th><th>Duration</th><th>Tests</th><th>Errors</th></thead>";

    for (var j = 0; j < d.jobs.length; j++) {
        var job = d.jobs[j];
        s += "<tr>";
        s += "<td>{0}</td><td>{1}</td>".ptFormat(job.id, pt_date2str(job.end));
        var hw = '';
        for (var h = 0; h < job.env_node.length; h++) {
            if (hw)
                hw += ', ';
            hw += job.env_node[h].name;
        }
        s += "<td>{0}</td><td>{1}</td><td><a href='/{2}/job/{3}'>{4}</a></td>".ptFormat(hw, job.suite_ver, d.project.id, job.id, job.title);
        if (job.tests_completed == job.tests_total)
            s += "<td>{0}</td><td>{1}</td><td>{2}</td>".ptFormat(job.duration, job.tests_completed, job.tests_errors);
        else
            s += "<td>{0}</td><td>{1} (of {2})</td><td>{3}</td>".ptFormat(job.duration, job.tests_completed, job.tests_total, job.tests_errors);
        s += "</tr>";
    }
    s += "</table></div>";
    s += "</div></div>"; // row, slider

    return s;
}

function pt_ajax_comparison_delete(comparison_id)
{
    if (!confirm('Are you sure you want to delete comparison #' + comparison_id + '?'))
        return false;

    $.ajax({
        url: '/api/v1.0/0/comparison/{0}'.ptFormat(comparison_id),
        cache: true,
        data: null,
        type: 'DELETE',
        timeout: 2000,
        success: function(data, status) {
            window.location.reload();
        },
        error: function(data, status, error) {
            alert("can't delete comparison #" + comparison_id + ", " + error);
        }
    });
    return false;
}

function pt_draw_regression_details(d, err_msg)
{
    var s = '';

    s += "<div class='pt_slider' id='regression_details_slider_{0}'>".ptFormat(d.id)

    if (err_msg) {
        s += "<div class='row'><div class='col-md-12'>";
        s += pt_draw_ajax_error(ptFormat(err_msg));
        s += "</div></div>";
        return s;
    }

    s += "<div class='row'>";

    s += "<div class='pt_obj_management'>" +
         "<a href='/admin/perftracker/regressionmodel/{0}/change/'>Edit</a><span>|</span>".ptFormat(d.id) +
         "<a onclick=\"alert('Sorry, not implemented');return false;\" >Download XLS</a></div>";

    s += "<div class='col-md-12'><h4>Jobs</h4>";
    s += "<table class='pt_obj_details'>";
    s += "<thead><th>#</th><th>Job end</th><th>Hw</th><th>Version</th><th>Title</th><th>Duration</th><th>Tests</th><th>Errors</th><th>Linked</th></thead>";

    var jobs = d.jobs_list;

    for (var j = 0; j < jobs.length; j++) {
        var job = jobs[j];
        s += "<tr>";
        s += "<td>{0}</td><td>{1}</td>".ptFormat(job.id, pt_date2str(job.end));
        var hw = '';
        for (var h = 0; h < job.env_node.length; h++) {
            if (hw)
                hw += ', ';
            hw += job.env_node[h].name;
        }
        s += "<td>{0}</td><td>{1}</td><td><a href='/{2}/job/{3}'>{4}</a></td>".ptFormat(hw, job.suite_ver, job.project.id, job.id, job.title);
        if (job.tests_completed == job.tests_total)
            s += "<td>{0}</td><td>{1}</td><td>{2}</td>".ptFormat(job.duration, job.tests_completed, job.tests_errors);
        else
            s += "<td>{0}</td><td>{1} (of {2})</td><td>{3}</td>".ptFormat(job.duration, job.tests_completed, job.tests_total, job.tests_errors);

        var showEditIcon = job.is_linked
            ? `<td><a href="#" data-id={0} data-toggle="modal" class="pt-link-job-edit pt-link-job-edit--linked glyphicon glyphicon-check"></a></td>`.ptFormat(job.id)
            : `<td><a href="#" data-id={0} data-toggle="modal" class="pt-link-job-edit pt-link-job-edit--unlinked glyphicon glyphicon-unchecked"></a></td>`.ptFormat(job.id);

        s += showEditIcon;
        s += "</tr>";
    }
    s += "</table></div>";
    s += "</div></div>"; // row, slider

    return s;
}

function pt_draw_hw_farm_node_details(d, err_msg)
{
    var s = '';
    var env_node = d.env_node;
    var vms = d.vms;
    var clients = d.clients;

    s += "<div class='pt_slider' id='hw_farm_node_details_slider_{0}'>".ptFormat(d.id)

    if (err_msg) {
        s += "<div class='row'><div class='col-md-12'>";
        s += pt_draw_ajax_error(ptFormat(err_msg));
        s += "</div></div>";
        return s;
    }

    s += "<div class='row'>";

    s += "<div class='pt_obj_management'>" +
         "<a href='/admin/perftracker/hwfarmnodemodel/{0}/change/'>Edit</a></div>".ptFormat(d.id);

    s += "<div class='col-md-12'><h4>Hardware node</h4>";
    s += "<table class='pt_obj_details'>";
    s += "<thead><th>Parameter</th><th>Value</th></thead>";

    s += "<tr><td>Node</td><td>#{0} - {1}</td></tr>".ptFormat(d.id, d.name);
    s += "<tr><td>Hostname</td><td>{0}</td></tr>".ptFormat(d.hostname);
    s += "<tr><td>IP</td><td>{0}</td></tr>".ptFormat(d.ip);
    s += "<tr><td>Model</td><td>{0} {1}</td></tr>".ptFormat(d.vendor, d.model);
    s += "<tr><td>CPU</td><td>{0} {1}</td></tr>".ptFormat(d.cpus_count, d.cpu_info);
    s += "<tr><td>RAM</td><td>{0} GB {1}</td></tr>".ptFormat(d.ram_gb, d.ram_info);
    s += "<tr><td>Storage</td><td>{0} TB {1}</td></tr>".ptFormat(d.storage_tb, d.storage_info);
    s += "<tr><td>Network</td><td>{0} Gb/s {1}</td></tr>".ptFormat(d.network_gbs, d.network_info);
    if (d.dashboard)
        s += "<tr><td>Dashboard</td><td><a href='{0}'>Link</a></td></tr>".ptFormat(d.dashboard);
    if (d.inv_id)
        s += "<tr><td>Inventory ID</td><td>{0}</td></tr>".ptFormat(d.inv_id);
    if (d.phys_location)
        s += "<tr><td>Phys location</td><td>{0}</td></tr>".ptFormat(d.phys_loation);
    s += "</table></div>";
    s += "</div>";

    if (d.cpu_score_up) {
        s += "<div class='row'>";
        s += "<div class='col-md-12'><h4>Performance scores</h4>";
        s += "<table id='perf_score_{0}' class='pt_obj_details'>".ptFormat(d.id);
        s += "<thead><th>Resource</th><th>UP score</th><th>SMP score</th></thead>";
        s += "<tr><td>CPU</td><td>{0}</td><td>{1}</td></tr>".ptFormat(d.cpu_score_up, d.cpu_score_smp);
        s += "<tr><td>RAM</td><td>{0}</td><td>{1}</td></tr>".ptFormat(d.ram_score_up, d.ram_score_smp);
        s += "<tr><td>Storage</td><td>{0}</td><td>{1}</td></tr>".ptFormat(d.storage_score_up, d.storage_score_smp);
        s += "<tr><td>Network</td><td>{0}</td><td>{1}</td></tr>".ptFormat(d.network_score_up, d.network_score_smp);
        s += "</tbody></table></div>";
        s += "</div></div>";
    }

    return s;
}

function pt_common_prefix(strings, words_boundary=true)
{
    var ar = strings.concat().sort();
    var a1 = ar[0];
    var a2 = ar[ar.length - 1];
    var l = a1.length, i= 0;

    while(i < l && a1.charAt(i) === a2.charAt(i))
        i++;

    var common_prefix = a1.substring(0, i);
    if (common_prefix.length == 0)
        return "";

    if (words_boundary) {
        var ar1 = strings[0].split(" ");
        var ar2 = common_prefix.split(" ");
        common_prefix = "";

        for (var i = 0; i < ar2.length; i++) {
            if (ar2[i] != ar1[i])
                break;
            if (common_prefix)
                common_prefix += " ";
            common_prefix += ar1[i];
        }
    }

    return common_prefix;
}

function pt_gen_comparison_title(job_ids, job_titles)
{
    if (job_titles.length == 0)
        return "Title";
    else if (job_titles.length == 1)
        return job_titles[0];

    if (!!job_titles.reduce(function(a, b){ return (a === b) ? a : NaN; })) {
        /* all equal */
        titles = [];
        for (var i = 0; i < job_titles.length; i++)
            titles.push(job_titles[i] + " #" + job_ids[i]);
        job_titles = titles;
    }

    console.log(job_titles);

    var title = pt_common_prefix(job_titles);
    var len = title.length;

    if (len == 0)
        return job_titles.join(" vs ");

    title += ": ";

    for (var i = 0; i < titles.length; i++) {
        if (i)
            title += " vs ";
        title += job_titles[i].substring(len, job_titles[i].length);
    }
    return title;
}

$(document).ready(function() {
    $('.pt_collapse.expanded').append('<span class="glyphicon glyphicon-triangle-bottom"></span>');
    $('.pt_collapse.collapsed').append('<span class="glyphicon glyphicon-triangle-right"></span>');
    $('.pt_collapse').on('click', function() {
        var x = $(this).hasClass('collapsed');
        if (x) {
            $(this).find(".glyphicon-triangle-right").removeClass("glyphicon-triangle-right").addClass("glyphicon-triangle-bottom");
        } else {
            $(this).find(".glyphicon-triangle-bottom").removeClass("glyphicon-triangle-bottom").addClass("glyphicon-triangle-right");
        }
    });
});

function pt_configure_chart(element, chart_type, has_failures, x_categories, x_name, x_type, x_rotate, y_name, series) {
    chart = echarts.init(document.getElementById(element));
    if (chart_type != 2 && chart_type != 4) {
        throw "Unsupported chart type " + chart_type;
    }
    var is_xy = (chart_type == 2);
    var legends = [];
    var option = {
        title: { },
        tooltip: {
            transitionDuration: 0,
            formatter: function(params) {
                var s = params.seriesName + "<br>";
                if (is_xy) {
                    if (params.data.errors)
                        s += params.data.value[0] + " : " + params.data.value[1] + "<br>"
                            + params.data.errors + " iteration(s) failed";
                    else
                        s += params.data[0] + " : " + params.data[1];
                } else {
                    if (params.data.errors)
                        s += params.data.value + "<br>" + params.data.errors + " iteration(s) failed";
                    else
                        s += params.data;
                }
                return s;
            }
        },
        legend: {
            data: legends,
            type: 'scroll',
            orient: 'vertical',
            right: 10,
            top: 50,
            width: 180,
            align: 'left'
        },
        xAxis: {
            data: x_categories,
            name: x_name,
            type: x_type,
            nameLocation: 'center',
            axisLabel: { rotate: x_rotate },
            nameGap: 30
        },
        yAxis: {
            name: y_name
        },
        grid: {
            top: 50,
            right: 200,
            left: 50
        },
        toolbox: {
            show: true,
            feature: {
                dataZoom: {
                    yAxisIndex: 'none'
                },
                dataView: {readOnly: false},
                magicType: {type: ['line', 'bar']},
                restore: {},
                saveAsImage: {}
            }
        },
        series: []
    };

    for (var i = 0; i < series.length; i++) {
        var s = series[i];
        var so = {
            name: s.name,
            data: s.data,
            animation: false
        };
        Object.assign(so, is_xy ? {
                type: 'line',
                smooth: true,
                smoothMonotone: 'none'
            } :
            {
                type: 'bar',
                barGap: '0.1'
            }
        );
        legends.push(so.name);
        option.series.push(so);

        if (s.trend) {
            var regr = ecStat.regression('polynomial', s.data, 3);
            regr.points.sort(function(a, b) { return a[0] - b[0]; });
            var trend = Object.assign({}, so, {
                    name: s.name + " (trend)",
                    data: regr.points,
                    showSymbol: false,
                    lineStyle: {
                        normal: {
                            color: 'gray',
                            width: 1,
                            type: 'dashed'
                        }
                    }
                });
            legends.push(trend.name);
            option.series.push(trend);
        }
    }
    if (has_failures)
        legends.push({"name": "Failed test", "icon": "diamond"});

    option.series.push(
        {name: 'Failed test', type: 'line', itemStyle: { color: '#000'}}
    );
    // console.log(JSON.stringify(option));
    chart.setOption(option);
}

function pt_configure_chart_async(element, chart_type, has_failures, x_categories, x_name, x_type, x_rotate, y_name, series) {
    var fn = function() {
        pt_configure_chart(element, chart_type, has_failures, x_categories, x_name, x_type, x_rotate, y_name, series);
    }
    setTimeout(fn, 0)
}

var tableConfig = {
    lengthMenu: [[50, 20, 200, 1000, -1], [50, 20, 200, 1000, "All"]],

    columnDefs: [
        {
            "targets": "colExpander",
            "type": "string",
            "orderable": false,
            "className": 'pt_row_details_toggle',
            "render": function (data, type, row) {
                return "<span class='glyphicon glyphicon-triangle-right' aria-hidden='true'></span>";
            }
        },
        {
            "targets": ["colId", "colCategory"],
            "type": "string",
            "visible": false,
        },
        {
            "targets": "colTag",
            "type": "string",
            "className": 'pt_left',
        },
        {
            "targets": "colScore",
            "type": "string",
            "className": 'pt_lborder',
        },
        {
            "targets": "colDeviation",
            "className": "pt_lborder pt_right",
            "type": "float",
            "render": function (data, type, row) {
                if (data === "-")
                    return data;
                return data + "%";
            }
        },
        {
            "targets": "colDiff",
            "width": "45px",
            "type": "string",
            "className": 'pt_diff_equal pt_right',
            "createdCell": function (td, cellData, rowData, rowIndex, colIndex) {
                var data = rowData[colIndex];
                var ar = data.split(" ");
                var diff = "";
                if (ar[1] === '1') {
                    $(td).attr('class', 'pt_diff_better pt_right');
                } else if (ar[1] === '-1') {
                    $(td).attr('class', 'pt_diff_worse pt_right');
                }
                diff = ar[0];
                if (ar[0] > 0) {
                    diff = "+" + diff;
                }
                if (diff !== "-") {
                    diff += "%";
                }
                $(td).html(diff);
            },
        },
    ]
};

function pt_configure_table(element, pageable, data) {
    var tableOpts = {
        "lengthMenu": tableConfig.lengthMenu,
        "bFilter": false,
        "data": data,
        "order": [[ 2, "asc" ]],
        "columnDefs": tableConfig.columnDefs
    };

    if (!pageable){
        tableOpts["bLengthChange"] = false;
        tableOpts["bInfo"] = false;
        tableOpts["bPaginate"] = false;
    }
    var table = $(element).DataTable(tableOpts);

    // Add event listener for opening and closing details
    $(element).on('click', 'td.pt_row_details_toggle', function () {
        // FIXME, merge with jobs.html
        var tr = $(this).closest('tr');
        var row = table.row( tr );
        var id = row.data()[1]; // FIXME: colId index

        if ( row.child.isShown() ) {
            // This row is already open - close it
            $(this)[0].innerHTML = "<span class='glyphicon glyphicon-triangle-right' aria-hidden='true'></span>";
            $('#test_details_slider_{0}'.ptFormat(id), row.child()).slideUp(function() {
                row.child.hide();
                tr.removeClass('shown');
            });
        }
        else {
            $(this)[0].innerHTML = "<span class='glyphicon glyphicon-triangle-bottom' aria-hidden='true'></span>";
            $.ajax({
                url: '/api/v1.0/13/comparison/476/group/0/test/{0}'.ptFormat(id),
                cache: true,
                data: null,
                type: 'GET',
                timeout: 2000,
                success: function(data, status) {
                    row.child(pt_test_details_draw(data, null)).show();
                    tr.next('tr').children().toggleClass('pt_row_details');
                    tr.addClass('shown');
                    tr.next('tr').children().find('.pt_slider').slideDown();
                },
                error: function(data, status, error) {
                    row.child(pt_test_details_draw(row.data(), error)).show();
                    tr.next('tr').children().toggleClass('pt_row_details');
                    tr.addClass('shown');
                    tr.next('tr').children().find('.pt_slider').slideDown();
                }
            });
        }
    });
}

function pt_configure_table_async(element, pageable, data) {
    var fn = function() {
        pt_configure_table(element, pageable, data);
    }
    setTimeout(fn, 0)
}

/*
 * Authentication stuff
 */

function initialize_nav_bar(api_ver) {
    $.ajax({
        url: '/api/v{0}/auth'.ptFormat(api_ver),
        data: null,
        type: 'GET',
        timeout: 2000,
        success: function (auth_response) {
            update_nav_bar(auth_response);
        },
        error: function (xhr) {
            console.log('Initializing navbar error: ' + xhr.status + ' ' + xhr.responseText);
        }
    });
}

function pt_login(api_ver) {
    var data = {
        email: $("#exampleInputEmail1").val(),
        password: $("#exampleInputPassword1").val(),
        action: 'login'
    };
    pt_auth_request(api_ver, data)
}

function pt_logout(api_ver) {
    var data = { action: 'logout' };
    pt_auth_request(api_ver, data)
}

function pt_auth_request(api_ver, data) {
    $.ajax({
        url: '/api/v{0}/auth'.ptFormat(api_ver),
        type: 'POST',
        contentType: "application/json",
        data: JSON.stringify(data),
        success: function (auth_response) {
            update_nav_bar(auth_response);
        },
        error: function (xhr) {
            console.log('Authentication error: ' + xhr.status + ' ' + xhr.responseText);
        }
    });
}

function update_nav_bar(auth_response) {
    document.getElementById("pt_username").style.display = auth_response.is_authenticated ? "list-item" : "none";
    document.getElementById("pt_btn_sign_in").style.display = auth_response.is_authenticated ? "none" : "list-item";
    document.getElementById("pt_btn_sign_out").style.display = auth_response.is_authenticated ? "list-item" : "none";
    $('#username').text(auth_response.username);
}