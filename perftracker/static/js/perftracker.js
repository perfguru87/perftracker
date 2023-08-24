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

function pt_date2str(dt, show_seconds = false) {
    if (typeof dt == 'undefined')
        return '';

    var now = new Date();
    var date = new Date(dt);  // string or Date object accepted
    var hrs = date.getHours();
    var mins = date.getMinutes();

    var year = (date.getFullYear() != now.getFullYear()) ? " " + date.toISOString().substring(0, 4) : "";

    var rv = date.getDate() + ' ' + date.ptGetShortMonth() + year + ', '
            + (hrs < 10 ? '0' + hrs : hrs) + ":" + (mins < 10 ? '0' + mins: mins);
    if (show_seconds) {
        var secs = date.getSeconds();
        rv += ":" + (secs < 10 ? '0' + secs: secs)
    }
    return rv;
}

function pt_daterange(begin, end, duration) {
    if (!begin && !end)
        return [];
    begin = begin || end;
    end = end || begin;
    var b = new Date(begin);
    var e = new Date(end);
    if (b.getMilliseconds() === e.getMilliseconds() && duration > 0) {
        b.setMilliseconds(e.getMilliseconds() - duration * 1000);
    }
    return [b, e];
}

function pt_daterange2str(begin, end, duration, show_seconds = false) {
    var rng = pt_daterange(begin, end, duration);
    if (!rng || rng.length == 0)
        return "";
    return pt_date2str(rng[0], show_seconds) + ' - ' + pt_date2str(rng[1], show_seconds) + " (local time)";
}

function pt_dur2str(duration) {
    var sec = duration % 60;
    var min = Math.floor(duration / 60) % 60;
    var hr = Math.floor(duration / 3600) % 24;
    var days = Math.floor(duration / 24 / 3600);
    var rv = days ? pt_pluralize(days, "day") + " " : "";
    rv += (rv || hr) ? hr + "h " : "";
    function z(x) { return (x < 10) ? "0" + x: "" + x; }
    return rv + z(min) + ":" + z(sec);
}

function pt_date2ISOstr(date) {
    const dateCopy = new Date(date);
    dateCopy.setSeconds(0, 0);
    dateCopy.setTime(dateCopy.getTime() - dateCopy.getTimezoneOffset() * (60 * 1000));
    return dateCopy.toISOString().replace('Z', '');
}

function pt_getHoursBeforeDate(date) {
    const now = new Date();
    return Math.round(Math.abs(date - now) / (60 * 60 * 1000));
}

function pt_getDeadlineByDuration(dateFrom, duration) {
    const deadline = new Date(dateFrom);
    deadline.setHours(deadline.getHours() + duration);
    return deadline;
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

function pt_draw_job_menu(id, deleted)
{
    var ret = "<a href='#' onclick=\"return pt_job_edit_cb({0})\">Edit</a><span>|</span>".ptFormat(id);
    if (deleted == 'True') {
        return ret + "<a href='#' onclick=\"return pt_job_undelete_cb({0})\">Undelete</a>".ptFormat(id); 
    }
    ret += "<a href='#' onclick=\"return pt_ajax_job_delete({0})\">Delete</a><span>|</span>".ptFormat(id);
    ret += "<a href='/0/job/{0}?as_json=1'>Download JSON</a><span>|</span>".ptFormat(id);
    ret += "<a onclick=\"alert('Sorry, not implemented');return false;\" >Download XLS</a>";
    return ret;
}

function pt_draw_job_details(d, err_msg, show_menu = true)
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
    if (show_menu)
        s += "<div class='pt_obj_management'>" + pt_draw_job_menu(d.id) + "</div>";
    s += "<div class='col-md-12'><h4>Test suite</h4>";
    s += "<table class='pt_obj_details'>";
    s += "<thead><th>Parameter</th><th>Value</th></thead>";

    if (d.product_name)
        s += "<tr><td>Product</td><td><b>{0} {1}</b></td></tr>".ptFormat(d.product_name, d.product_ver);

    if (d.links) {
        var links = pt_draw_links(d.links);
        if (links)
            s += "<tr><td>Links</td><td>{0}</td></tr>".ptFormat(links);
    }

    s += "<tr><td>Job #</td><td>{0}</td></tr>".ptFormat(d.id)
    s += "<tr><td>UUID</td><td>{0}</td></tr>".ptFormat(d.uuid)
    s += "<tr><td>Duration</td><td>{0}, time: {1}, uploaded: {2}</td></tr>".ptFormat(
        pt_dur2str(d.duration), pt_daterange2str(d.begin, d.end, d.duration), pt_date2str(d.upload));
    if (d.cmdline)
        s += "<tr><td>Cmdline</td><td class='pt_ellipsis'>{0}</td></tr>".ptFormat(d.cmdline);

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

function pt_ajax_job_details(api_ver, project_id, job_id, show_menu = true)
{
    $.ajax({
        url: '/api/v' + api_ver + '/' + project_id + '/job/{0}'.ptFormat(job_id),
        cache: true,
        data: null,
        type: 'GET',
        timeout: 2000,
        success: function(data, status) {
            $('#job_details_{0}'.ptFormat(job_id)).html(pt_draw_job_details(data, null, show_menu));
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

function pt_draw_comparison_menu(project_id, id, deleted)
{
    var ret = "<a onclick=\"window.location.replace('/{0}/job/?edit={1}');return false;\" >Edit</a><span>|</span>".ptFormat(project_id, id);
    if (deleted == 'True') {
       return ret + "<a onclick=\"window.location.replace('/{0}/job/?edit={1}');return false;\" >Undelete</a>".ptFormat(project_id, id);
    }
    ret += "<a href='#' onclick=\"return pt_ajax_comparison_delete({0})\">Delete</a><span>|</span>".ptFormat(id);
    ret += "<a onclick=\"alert('Sorry, not implemented');return false;\" >Download XLS</a><span>|</span>";
    ret += "<a onclick=\"pt_label_data()\">Label data</a>";
    return ret;
}

function pt_draw_comparison_details(d, err_msg)
{
    var s = '';
    var env_node = d.env_node;
    var vms = d.vms;
    var clients = d.clients;

    s += "<div class='pt_slider' id='comparison_details_slider_{0}'>".ptFormat(d.id);

    if (err_msg) {
        s += "<div class='row'><div class='col-md-12'>";
        s += pt_draw_ajax_error(ptFormat(err_msg));
        s += "</div></div>";
        return s;
    }

    s += "<div class='row'>";
    s += "<div class='pt_obj_management'>" + pt_draw_comparison_menu(d.project.id, d.id) + "</div>";
    s += "<div class='col-md-12'><h4>Jobs</h4>";
    s += "<table class='pt_obj_details'>";
    s += "<thead><th>#</th><th>Job end</th><th>Hw</th><th>Version</th><th>Title</th><th>Duration</th>" +
         "<th>Tests</th><th>Tests<br>with<br>errors</th><th>Test<br>cases</th><th>Test cases<br>with<br>errors</th></thead>";

    for (var j = 0; j < d.jobs.length; j++) {
        var job = d.jobs[j];
        var link = '/{0}/job/{1}'.ptFormat(d.project.id, job.id);
        s += "<tr>";
        s += "<td><a href='{0}'>{1}</a></td><td>{2}</td>".ptFormat(link, job.id, pt_date2str(job.end));
        var hw = '';
        for (var h = 0; h < job.env_node.length; h++) {
            if (hw)
                hw += ', ';
            hw += job.env_node[h].name;
        }
        s += "<td>{0}</td><td>{1}</td><td><a href='{2}'>{3}</a></td>".ptFormat(hw, job.suite_ver, link, job.title);
        if (job.tests_completed == job.tests_total)
            s += "<td>{0}</td><td>{1}</td><td>{2}</td><td>{3}</td><td>{4}</td>".ptFormat(pt_dur2str(job.duration),
                job.tests_completed, job.tests_errors, job.testcases_total, job.testcases_errors);
        else
            s += "<td>{0}</td><td>{1} (of {2})</td><td>{3}</td><td>{4}</td><td>{5}</td>".ptFormat(pt_dur2str(job.duration),
                job.tests_completed, job.tests_total, job.tests_errors, job.testcases_total, job.testcases_errors);
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

function pt_draw_regression_menu(d)
{
    return "<a href='/admin/perftracker/regressionmodel/{0}/change/'>Edit</a><span>|</span>".ptFormat(d.id) +
           "<a onclick=\"alert('Sorry, not implemented');return false;\" >Download XLS</a>";
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
    s += "<div class='pt_obj_management'>" + pt_draw_regression_menu(d) + "</div>";
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

function pt_handle_collapsing(selector, callback) {
    $(selector).on('click', function() {
        el = $(this);
        var x = el.hasClass('collapsed');
        if (x) {
            el.find(".glyphicon-triangle-right").removeClass("glyphicon-triangle-right").addClass("glyphicon-triangle-bottom");
            callback && callback(el, false);
        } else {
            el.find(".glyphicon-triangle-bottom").removeClass("glyphicon-triangle-bottom").addClass("glyphicon-triangle-right");
            callback && callback(el, true);
        }
    });
}

$(document).ready(function() {
    $('.pt_collapse.expanded').append('<span class="glyphicon glyphicon-triangle-bottom"></span>');
    $('.pt_collapse.collapsed').append('<span class="glyphicon glyphicon-triangle-right"></span>');
    pt_handle_collapsing('.pt_collapse');
});

function pt_configure_chart(element, chart_type, has_failures, x_categories, x_name, x_type, x_rotate, y_name, series) {
    chart = echarts.init(document.getElementById(element));
    if (chart_type !== 2 && chart_type !== 4) {
        throw "Unsupported chart type " + chart_type;
    }
    var is_xy = (chart_type === 2);
    var legends = [];
    var option = {
        title: {
            subtext: series[0].less_better ? '[lower is better]' : '[higher is better]',
            x: 'center',
        },
        animation: false,
        tooltip: {
            transitionDuration: 0,
            formatter: function(params) {
                var s = params.seriesName + "<br>";
                if (is_xy) {
                    if (params.data.errors)
                        s += params.data.value[0] + " : " + params.data.value[1] + "<br>" + params.data.errors;
                    else
                        s += params.data[0] + " : " + params.data[1];
                } else {
                    if (params.data.errors)
                        s += params.data.value + "<br>" + params.data.errors;
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
                magicType: {type: ['line', 'bar']},
                saveAsImage: {},
                myFullScreen: {
                    show: true,
                    title: 'Toggle Fullscreen',
                    icon: 'M0 0v20h23V0L0 0zM19 13 19 17M15 17 19 17M15 13 19 17zM19 7 19 3 15 3 19 3 15 7 19 3zM4 13 4 17 8 17 4 17 8 13M8 3 4 3 4 7 4 3 8 7',
                    onclick: function() {
                        $('.pt_modal_chart').fadeIn();
                        $('.pt_modal_close_btn').on('click', function() { $('.pt_modal_chart').fadeOut(); });
                        $('#pt_modal_content').empty();
                        $(".pt_modal_chart_title").html($("#" + element).prev("h4:first").text());
                        $('#pt_modal_content').append("<div id='pt_modal_content_chart' style='min-height: 100%; height: 100%;'></div>");
                        pt_configure_chart("pt_modal_content_chart", chart_type, has_failures, x_categories, x_name, x_type, x_rotate, y_name, series);
                    }
                },
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


function pt_cmp_table_html(element, titles) {
    var s =
"<table id='" + element + "' class='display dataTable' cellspacing='0' width='100%'>\
   <thead>\
     <tr>\
       <th colspan='4'></th>";
       titles.forEach(function(title, index) {
           s += "<th class='pt_job' colspan='{0}'>{1}</th>".ptFormat(index + 3, title);
       });

       s +=
    "</tr>\
     <tr>\
       <th class='colExpander'></th>\
       <th class='colId'></th>\
       <th class='colSeqNum'>#</th>\
       <th class='colTag pt_left'>Tag</th>";
       titles.forEach(function(title, index) {
           s +=
              "<th class='colScore pt_lborder'>Score</th>" +
              "<th class='colDeviation pt_right'>&plusmn;%</th>" +
              "<th class='colHidden'/>";
           for(var i = 1; i <= index; i++) {
               s += "<th class='colDiff pt_lborder pt_right'>% vs #{0}</th>".ptFormat(i);
           }
       });
       s +=
     "</tr>\
   </thead>\
</table>";

    return s;
}

var pt_cmp_table_config = {
    lengthMenu: [[20, 50, 200, -1], [20, 50, 200, "All"]],

    columnDefs: [
        {
            "targets": "colTag",
            "type": "string",
            "className": 'pt_left',
        },
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
            "targets": ["colId", "colCategory", "colHidden"],
            "type": "string",
            "visible": false,
        },
        {
            "targets": "colScore",
            "type": "string",
            "className": 'pt_lborder',
            "createdCell": function (td, cellData, rowData, rowIndex, colIndex) {
                var errors = rowData[colIndex + 2];
                if (errors) {
                    $(td).addClass("pt_test_errors");
                    errors = "<br><span class='pt_smaller'>" + errors + "</span>";
                }
                $(td).html(cellData + errors);
            }
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

function pt_cmp_configure_table(container, table_id, job_titles, pageable, data, tag_modifier, testlink) {
    var tableOpts = {
        "lengthMenu": pt_cmp_table_config.lengthMenu,
        "bFilter": false,
        "data": data,
        "order": [[ 2, "asc" ]],
        "columnDefs": pt_cmp_table_config.columnDefs
    };

    if (tag_modifier) {  // override tag column rendering
        tableOpts.columnDefs = tableOpts.columnDefs.map(def => def); // new array, old values
        tableOpts.columnDefs[0] = Object.assign({}, tableOpts.columnDefs[0], {
            "render": function (data, type, row) {
                return tag_modifier(data);
            }
        });
    }
    if (!pageable){
        tableOpts.bLengthChange = false;
        tableOpts.bInfo = false;
        tableOpts.bPaginate = false;
    }

    container.append(pt_cmp_table_html(table_id, all_jobs));

    var tab_el = $("#" + table_id);
    var table = tab_el.DataTable(tableOpts);

    // Add event listener for opening and closing details
    tab_el.on('click', 'td.pt_row_details_toggle', function () {
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
                url: testlink + id,
                cache: true,
                data: null,
                type: 'GET',
                timeout: 2000,
                success: function(data, status) {
                    row.child(pt_cmp_test_details_draw(data, null)).show();
                    tr.next('tr').children().toggleClass('pt_row_details');
                    tr.addClass('shown');
                    tr.next('tr').children().find('.pt_slider').slideDown();
                },
                error: function(data, status, error) {
                    row.child(pt_cmp_test_details_draw(row.data(), error)).show();
                    tr.next('tr').children().toggleClass('pt_row_details');
                    tr.addClass('shown');
                    tr.next('tr').children().find('.pt_slider').slideDown();
                }
            });
        }
    });
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
        encoded_email: window.btoa($("#exampleInputEmail1").val()),
        encoded_password: window.btoa($("#exampleInputPassword1").val()),
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

function pt_getCurrentUserInfo(api_ver) {
    var userInfo = {
        isAuthenticated: false,
        username: 'AnonymousUser',
    };
    $.ajax({
        url: '/api/v{0}/auth'.ptFormat(api_ver),
        type: 'GET',
        async: false,
        success: function (data) {
            userInfo.isAuthenticated = data.is_authenticated;
            userInfo.username = data.username;
        },
        error: function (xhr) {
            alert('Error: ' + xhr.status + ' ' + xhr.responseText);
        }
    });
    return userInfo;
}

function update_nav_bar(auth_response) {
    document.getElementById("pt_username").style.display = auth_response.is_authenticated ? "list-item" : "none";
    document.getElementById("pt_btn_sign_in").style.display = auth_response.is_authenticated ? "none" : "list-item";
    document.getElementById("pt_btn_sign_out").style.display = auth_response.is_authenticated ? "list-item" : "none";
    $('#username').text(auth_response.username);
}

function test_errors2str(data) {
    var rv = "";
    if (data.errors) {
        rv = String(data.errors) + " errors";
    }
    if (data.status === "FAILED") {
        rv += rv ? ", ": "";
        rv += data.status;
    }
    return rv;
}

function pt_job_test_details_draw(d, err_msg)
{
    var s = '';
    var env_node = d.env_node;
    var vms = d.vms;
    var clients = d.clients;

    console.log(d);

    s += "<div class='pt_slider' id='test_details_slider_{0}'>".ptFormat(d.id);

    s += "<div class='row'>";

    s += "<div class='col-md-4'>";
    s += "<h4>Test details</h4>";
    s += "<table class='pt_obj_details'>";
    s += "<thead><th>Parameter</th><th>Value</th></thead></tbody>";
    s += "<tr><td>Raw scores</td><td>{0} {1}</td></tr>".ptFormat(d.scores, d.metrics);
    s += "<tr><td>&plusmn; %</td><td>{0}</td></tr>".ptFormat(d.avg_plusmin);
    var errors = test_errors2str(d);
    var estyle = errors ? " class='pt_test_errors'" : "";
    s += "<tr><td>Errors</td><td{0}>{1}</td></tr>".ptFormat(estyle, errors);
    s += "<tr><td>Raw deviations</td><td>{0}</td></tr>".ptFormat(d.deviations);
    s += "<tr><td>Test loops</td><td>{0}</td></tr>".ptFormat(d.loops ? d.loops : 'n/a');
    s += "<tr><td>Duration (s)</td><td>{0}</td></tr>".ptFormat(d.duration);
    s += "<tr><td>Timing</td><td>{0}</td></tr>".ptFormat(pt_daterange2str(d.begin, d.end, d.duration, true));
    s += "</tbody></table>";
    s += "</div>";

    s += "<div class='col-md-8'>";
    s += "<h4>Test info</h4>";
    s += "<table class='pt_obj_details'>";
    s += "<thead><th>Parameter</th><th>Value</th></thead><tbody>";
    s += "<tr><td>Score</td><td>{0} {1} ({2})</td></tr>".ptFormat(d.avg_score, d.metrics, d.less_better ? 'smaller is better' : 'bigger is better');
    s += "<tr><td>Cmdline</td><td><span class='pt_ellipsis'>{0}</td></tr>".ptFormat(d.cmdline);
    s += "<tr><td>Description</td><td>{0}</td></tr>".ptFormat(d.description);

    s += "<tr><td>Group</td><td>{0}</td></tr>".ptFormat(d.group);
    s += "<tr><td>Category</td><td>{0}</td></tr>".ptFormat(d.category);

    s += "<tr><td>Attributes</td><td>{0}</td></tr>".ptFormat(d.attribs ? pt_draw_attribs(d.attribs) : "");
    s += "<tr><td>Links</td><td>{0}</td></tr>".ptFormat(d.links ? pt_draw_links(d.links) : "");
    s += "</tbody></table>";
    s += "</div>";


    s += "</div>"; /* row */

    s += "</div>"; /* pt_slider */

    return s;
}

function pt_cmp_test_details_draw_row(title, ar, func) {
    var s = '<tr><td>' + title + '</td>';
    for (n = 0; n < ar.length; n++) {
        var c = func(ar[n]);
        if (!c && !ar[n].id)
            c = '-';
        if (!c.startsWith("<td"))
            c = '<td>' + c + '</td>';
        s += c;
    }
    return s + '</tr>';
}

function pt_cmp_test_details_draw(ar, err_msg) {
    var s = '';
    var d = ar[0];
    var env_node = d.env_node;
    var vms = d.vms;
    var clients = d.clients;

    s += "<div class='pt_slider' id='test_details_slider_{0}'>".ptFormat(d.id);

    s += "<div class='row'>";

    s += "<div class='col-md-12'>";
    s += "<h4>Test details</h4>";
    s += "<table class='pt_obj_details'>";
    s += "<thead><th>Parameter</th><th colspan='" + ar.length + "'>Values</th></thead></tbody>";
    s += pt_cmp_test_details_draw_row('ID', ar, function(d) { return "{0}".ptFormat(d.id);});
    s += pt_cmp_test_details_draw_row('Scores', ar, function(d) { return "{0}".ptFormat(d.avg_score);});
    s += "<tr><td>Metrics</td><td colspan='" + ar.length + "'>" + "{0} ({1})".ptFormat(
           d.metrics, d.less_better ? 'smaller is better' : 'bigger is better') + "</td></tr>";
    s += "<tr><td>Group</td><td colspan='" + ar.length + "'>" + "{0}</td></tr>".ptFormat(d.group);
    s += "<tr><td>Category</td><td colspan='" + ar.length + "'>{0}</td></tr>".ptFormat(d.category);
    s += pt_cmp_test_details_draw_row('Cmdlines', ar, function(d) { return d.cmdline ? "<span class='pt_ellipsis'>{0}</span>".ptFormat(d.cmdline) : d.cmdline;});
    s += pt_cmp_test_details_draw_row('Descriptions', ar, function(d) { return d.description ? "<span class='pt_ellipsis'>{0}</span>".ptFormat(d.description) : d.description;});
    s += pt_cmp_test_details_draw_row('Raw scores', ar, function(d) { return "{0}".ptFormat(d.scores); });
    s += pt_cmp_test_details_draw_row('Errors', ar, function(d) {
        var errors = test_errors2str(d);
        var inner = errors ? "<td class='pt_test_errors'>{0}</td>" : "{0}";
        return inner.ptFormat(errors);
    });
    s += pt_cmp_test_details_draw_row('Raw deviations', ar, function(d) { return "{0}".ptFormat(d.deviations); });
    s += pt_cmp_test_details_draw_row('Test loops', ar, function(d) { return "{0}".ptFormat(d.id ? (d.loops || 'n/a') : ""); });
    s += pt_cmp_test_details_draw_row('Duration (s)', ar, function(d) { return "{0}".ptFormat(d.duration); });
    s += pt_cmp_test_details_draw_row('Timing', ar, function(d) { return "{0}".ptFormat(pt_daterange2str(d.begin, d.end, d.duration, true)); });
    s += pt_cmp_test_details_draw_row('Links', ar, function(d) { return "{0}".ptFormat(d.links ? pt_draw_links(d.links) : ""); });
    s += "</tbody></table>";
    s += "</div>";

    s += "</div>"; /* row */

    s += "</div>"; /* pt_slider */

    return s;
}

function pt_isInViewport(elem) {
    var bounding = elem.getBoundingClientRect();
    return (
        bounding.bottom > 5 &&
        bounding.right >= 0 &&
        bounding.top <= (window.innerHeight || document.documentElement.clientHeight) &&
        bounding.left <= (window.innerWidth || document.documentElement.clientWidth)
    );
}

function pt_pluralize(count, noun, suffix = 's') {
    return `${count} ${noun}${count !== 1 ? suffix : ''}`;
}

function pt_comparison_enable_disable_buttons(enable) {
    if (enable) {
        $("#pt_btn_save").prop("disabled", false);
        $("#pt_btn_preview").prop("disabled", false);
    } else {
        $("#pt_btn_save").prop("disabled", true);
        $("#pt_btn_preview").prop("disabled", true);
    }
}
