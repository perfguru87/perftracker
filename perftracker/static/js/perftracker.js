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
                 !isNaN(parseInt(j['cpus'])) ? "{0} CPUs".ptFormat(j['cpus']) : '',
                 !isNaN(parseInt(j['ram_mb'])) ? "{0} GB RAM".ptFormat(j['ram_mb'] / 1024.0) : '',
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
         "<a href='/admin/perftracker/jobmodel/{0}/change/'>Edit</a><span>|</span>".ptFormat(d.id) +
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
         "<a href='/admin/perftracker/comparisonmodel/{0}/change/'>Edit</a><span>|</span>".ptFormat(d.id) +
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
        s += "<td>{0}</td><td>{1}</td><td><a href='/{2}/job/{3}'>{4}</a></td>".ptFormat(hw, job.suite_ver, d.project, job.id, job.title);
        s += "<td>{0}</td><td>{1} (of {2})</td><td>{3}</td>".ptFormat(job.duration, job.tests_completed, job.tests_total, job.tests_errors);
        s += "</tr>";
    }
    s += "</table></div>";
    s += "</div></div>"; // row, slider

    return s;
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
